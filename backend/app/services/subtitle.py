import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.assembly import AssemblyScene, AssemblyTimeline
from app.models.audio_clip import AudioClip
from app.models.scene import Scene
from app.models.story import Story


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fmt_float(value: Any) -> float:
    return round(float(value or 0.0), 4)


def _flatten_dialogue(value: Any) -> List[str]:
    out: List[str] = []
    if value is None:
        return out
    if isinstance(value, str):
        text = value.strip()
        if text:
            out.append(text)
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(_flatten_dialogue(item))
        return out
    if isinstance(value, dict):
        preferred = ("text", "line", "dialogue", "content", "utterance")
        for key in preferred:
            if key in value:
                out.extend(_flatten_dialogue(value[key]))
                return out
        for key in sorted(value.keys()):
            out.extend(_flatten_dialogue(value[key]))
    return out


def _srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(segments: Iterable[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        text = str(seg.get("text") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        blocks.append(
            f"{idx}\n{_srt_timestamp(float(seg['start_time']))} --> {_srt_timestamp(float(seg['end_time']))}\n{text}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


class SubtitleService:
    """Core V1 deterministic subtitle state bound to an AssemblyTimeline.

    No ASR, translation, or paid provider calls are performed. Source text comes
    only from existing VO/DIALOGUE prompts or Scene narration/dialogue.
    """

    @staticmethod
    def _resolve_timeline(db: Session, project_id: uuid.UUID, timeline_id: Optional[str] = None) -> AssemblyTimeline:
        query = db.query(AssemblyTimeline).filter(AssemblyTimeline.project_id == project_id)
        if timeline_id:
            try:
                tid = uuid.UUID(str(timeline_id))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid timeline_id") from exc
            timeline = query.filter(AssemblyTimeline.id == tid).first()
        else:
            timeline = query.filter(AssemblyTimeline.is_active.is_(True)).first()
            if not timeline:
                timeline = query.order_by(AssemblyTimeline.version.desc()).first()
        if not timeline:
            raise HTTPException(status_code=404, detail="No assembly timeline found for project")
        return timeline

    @staticmethod
    def _ordered_scene_placements(timeline: AssemblyTimeline) -> List[Tuple[AssemblyScene, List[Any]]]:
        result: List[Tuple[AssemblyScene, List[Any]]] = []
        for assembly_scene in sorted(timeline.scenes, key=lambda sc: (sc.scene_order, str(sc.id))):
            placements = sorted(
                assembly_scene.shot_placements,
                key=lambda p: (p.shot_order, getattr(p.shot, "shot_number", 0), str(p.id)),
            )
            result.append((assembly_scene, placements))
        return result

    @classmethod
    def _placement_intervals(cls, timeline: AssemblyTimeline) -> Dict[str, Tuple[float, float]]:
        ordered = [p for _, placements in cls._ordered_scene_placements(timeline) for p in placements]
        intervals: Dict[str, Tuple[float, float]] = {}
        cursor = 0.0
        for idx, placement in enumerate(ordered):
            duration = max(0.1, float(placement.effective_duration or 0.0))
            start = cursor
            end = start + duration
            intervals[str(placement.id)] = (round(start, 4), round(end, 4))
            overlap = 0.0
            if idx < len(ordered) - 1 and str(placement.transition_to_next or "CUT").upper() in ("FADE", "DISSOLVE"):
                next_duration = max(0.1, float(ordered[idx + 1].effective_duration or 0.0))
                overlap = min(0.5, duration / 2.0, next_duration / 2.0)
            cursor = max(start, end - overlap)
        return intervals

    @classmethod
    def _source_snapshot(cls, db: Session, timeline: AssemblyTimeline) -> Dict[str, Any]:
        scene_rows: List[Dict[str, Any]] = []
        shot_keys: List[Tuple[int, int, uuid.UUID]] = []
        for assembly_scene, placements in cls._ordered_scene_placements(timeline):
            scene: Optional[Scene] = assembly_scene.scene
            scene_number = int(getattr(scene, "scene_number", assembly_scene.scene_order + 1))
            scene_rows.append({
                "scene_number": scene_number,
                "scene_order": int(assembly_scene.scene_order),
                "narration": (getattr(scene, "narration", None) or "").strip(),
                "dialogue": _flatten_dialogue(getattr(scene, "dialogue", None)),
                "placements": [
                    {
                        "shot_number": int(getattr(p.shot, "shot_number", p.shot_order + 1)),
                        "shot_order": int(p.shot_order),
                        "source_type": str(p.source_type or ""),
                        "trim_in": _fmt_float(p.trim_in),
                        "trim_out": _fmt_float(p.trim_out) if p.trim_out is not None else None,
                        "effective_duration": _fmt_float(p.effective_duration),
                        "still_duration": _fmt_float(p.still_duration),
                        "transition_to_next": str(p.transition_to_next or "CUT").upper(),
                        "placement_version": int(p.version or 1),
                    }
                    for p in placements
                ],
            })
            for p in placements:
                shot_keys.append((scene_number, int(getattr(p.shot, "shot_number", p.shot_order + 1)), p.shot_id))

        audio_rows = db.query(AudioClip).filter(
            AudioClip.project_id == timeline.project_id,
            AudioClip.audio_type.in_(["VO", "DIALOGUE"]),
        ).all()
        by_shot_semantic: List[Dict[str, Any]] = []
        shot_semantic = {shot_id: (scene_no, shot_no) for scene_no, shot_no, shot_id in shot_keys}
        for clip in audio_rows:
            text = (clip.prompt or "").strip()
            if not text or clip.mute:
                continue
            scene_no, shot_no = shot_semantic.get(clip.shot_id, (0, 0))
            by_shot_semantic.append({
                "scene_number": scene_no,
                "shot_number": shot_no,
                "audio_type": str(clip.audio_type),
                "name": str(clip.name or ""),
                "prompt": text,
                "language": str(clip.language or ""),
                "version": int(clip.version or 1),
                "start_time": _fmt_float(clip.start_time),
                "duration_seconds": _fmt_float(clip.duration_seconds) if clip.duration_seconds is not None else None,
            })
        by_shot_semantic.sort(key=lambda r: (
            r["scene_number"], r["shot_number"], r["audio_type"], r["name"], r["version"], r["prompt"]
        ))
        return {
            "timeline_version": int(timeline.version),
            "scenes": scene_rows,
            "voice_sources": by_shot_semantic,
        }

    @classmethod
    def compute_timeline_fingerprint(cls, db: Session, timeline: AssemblyTimeline) -> str:
        payload = cls._source_snapshot(db, timeline)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _split_interval(start: float, end: float, count: int) -> List[Tuple[float, float]]:
        if count <= 0:
            return []
        duration = max(0.1, end - start)
        step = duration / count
        result = []
        for idx in range(count):
            seg_start = start + step * idx
            seg_end = end if idx == count - 1 else start + step * (idx + 1)
            result.append((round(seg_start, 3), round(max(seg_start + 0.05, seg_end), 3)))
        return result

    @classmethod
    def _generate_segments(cls, db: Session, timeline: AssemblyTimeline, language: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        intervals = cls._placement_intervals(timeline)
        audio_rows = db.query(AudioClip).filter(
            AudioClip.project_id == timeline.project_id,
            AudioClip.audio_type.in_(["VO", "DIALOGUE"]),
        ).all()
        by_shot: Dict[uuid.UUID, List[AudioClip]] = {}
        for clip in audio_rows:
            if clip.shot_id and (clip.prompt or "").strip() and not clip.mute:
                by_shot.setdefault(clip.shot_id, []).append(clip)
        for clips in by_shot.values():
            clips.sort(key=lambda c: (float(c.start_time or 0.0), str(c.audio_type), c.name, str(c.id)))

        segments: List[Dict[str, Any]] = []
        source_counts = {"SHOT_AUDIO": 0, "SCENE_TEXT": 0}

        for assembly_scene, placements in cls._ordered_scene_placements(timeline):
            scene: Optional[Scene] = assembly_scene.scene
            scene_number = int(getattr(scene, "scene_number", assembly_scene.scene_order + 1))
            shot_audio_present = any(by_shot.get(p.shot_id) for p in placements)

            if shot_audio_present:
                for placement in placements:
                    clips = by_shot.get(placement.shot_id, [])
                    if not clips:
                        continue
                    start, end = intervals[str(placement.id)]
                    windows = cls._split_interval(start, end, len(clips))
                    shot_number = int(getattr(placement.shot, "shot_number", placement.shot_order + 1))
                    for clip, (seg_start, seg_end) in zip(clips, windows):
                        seg_language = str(clip.language or language)
                        segments.append({
                            "id": str(uuid.uuid4()),
                            "ordinal": 0,
                            "text": (clip.prompt or "").strip(),
                            "start_time": seg_start,
                            "end_time": seg_end,
                            "language": seg_language,
                            "source_type": "SHOT_AUDIO",
                            "source_ref": f"scene:{scene_number}/shot:{shot_number}/{clip.audio_type}:{clip.name}",
                        })
                        source_counts["SHOT_AUDIO"] += 1
            else:
                texts: List[Tuple[str, str]] = []
                narration = (getattr(scene, "narration", None) or "").strip()
                if narration:
                    texts.append(("SCENE_NARRATION", narration))
                for idx, line in enumerate(_flatten_dialogue(getattr(scene, "dialogue", None)), start=1):
                    if line.strip():
                        texts.append((f"SCENE_DIALOGUE_{idx}", line.strip()))
                if texts and placements:
                    scene_start = intervals[str(placements[0].id)][0]
                    scene_end = intervals[str(placements[-1].id)][1]
                    windows = cls._split_interval(scene_start, scene_end, len(texts))
                    for (source_type, text), (seg_start, seg_end) in zip(texts, windows):
                        segments.append({
                            "id": str(uuid.uuid4()),
                            "ordinal": 0,
                            "text": text,
                            "start_time": seg_start,
                            "end_time": seg_end,
                            "language": language,
                            "source_type": source_type,
                            "source_ref": f"scene:{scene_number}/{source_type.lower()}",
                        })
                        source_counts["SCENE_TEXT"] += 1

        segments.sort(key=lambda s: (s["start_time"], s["end_time"], s["source_ref"], s["text"]))
        last_end = 0.0
        for idx, segment in enumerate(segments, start=1):
            start = max(last_end, float(segment["start_time"]))
            end = max(start + 0.05, float(segment["end_time"]))
            segment["ordinal"] = idx
            segment["start_time"] = round(start, 3)
            segment["end_time"] = round(end, 3)
            last_end = end

        if not segments:
            raise HTTPException(
                status_code=400,
                detail="No authoritative subtitle text found. Add VO/DIALOGUE prompt text or Scene narration/dialogue before generating subtitles.",
            )

        return segments, {
            "segment_count": len(segments),
            "shot_audio_segments": source_counts["SHOT_AUDIO"],
            "scene_text_segments": source_counts["SCENE_TEXT"],
            "generation_policy": "DETERMINISTIC_AUTHORITATIVE_TEXT_ONLY",
        }

    @staticmethod
    def _state(timeline: AssemblyTimeline) -> Dict[str, Any]:
        raw = timeline.subtitle_state if isinstance(timeline.subtitle_state, dict) else {}
        history = raw.get("history") if isinstance(raw.get("history"), list) else []
        active = raw.get("active") if isinstance(raw.get("active"), dict) else None
        return {"active": active, "history": list(history)}

    @staticmethod
    def _store_state(db: Session, timeline: AssemblyTimeline, state: Dict[str, Any]) -> None:
        timeline.subtitle_state = state
        flag_modified(timeline, "subtitle_state")
        db.add(timeline)
        db.commit()
        db.refresh(timeline)

    @classmethod
    def _is_stale(cls, db: Session, timeline: AssemblyTimeline, track: Dict[str, Any]) -> bool:
        return (
            int(track.get("timeline_version", -1)) != int(timeline.version)
            or str(track.get("timeline_fingerprint") or "") != cls.compute_timeline_fingerprint(db, timeline)
        )

    @classmethod
    def _read_track(cls, db: Session, timeline: AssemblyTimeline, track: Dict[str, Any]) -> Dict[str, Any]:
        return {**track, "is_stale": cls._is_stale(db, timeline, track)}

    @classmethod
    def get_active(cls, db: Session, project_id: uuid.UUID, timeline_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        timeline = cls._resolve_timeline(db, project_id, timeline_id)
        active = cls._state(timeline)["active"]
        return cls._read_track(db, timeline, active) if active else None

    @classmethod
    def generate(
        cls,
        db: Session,
        project_id: uuid.UUID,
        timeline_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        timeline = cls._resolve_timeline(db, project_id, timeline_id)
        story = db.query(Story).filter(Story.project_id == project_id).first()
        resolved_language = (language or (story.language if story else None) or "und").strip() or "und"
        fingerprint = cls.compute_timeline_fingerprint(db, timeline)
        segments, source_summary = cls._generate_segments(db, timeline, resolved_language)
        srt_content = build_srt(segments)
        srt_sha256 = hashlib.sha256(srt_content.encode("utf-8")).hexdigest()

        state = cls._state(timeline)
        previous = state.get("active")
        history = state.get("history", [])
        if previous:
            history.append(previous)
        version_number = int(previous.get("version_number", 0)) + 1 if previous else 1
        track = {
            "id": str(uuid.uuid4()),
            "version_number": version_number,
            "timeline_version": int(timeline.version),
            "timeline_fingerprint": fingerprint,
            "language": resolved_language,
            "enabled": True,
            "render_mode": "OFF",
            "review_status": "GENERATED",
            "is_reviewed": False,
            "source_summary": source_summary,
            "segments": segments,
            "srt_content": srt_content,
            "srt_sha256": srt_sha256,
            "created_at": utc_now_iso(),
            "reviewed_at": None,
        }
        cls._store_state(db, timeline, {"active": track, "history": history})
        return cls._read_track(db, timeline, track)

    @classmethod
    def review(
        cls,
        db: Session,
        project_id: uuid.UUID,
        enabled: bool,
        render_mode: str,
        timeline_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        timeline = cls._resolve_timeline(db, project_id, timeline_id)
        state = cls._state(timeline)
        active = state.get("active")
        if not active:
            raise HTTPException(status_code=404, detail="Generate subtitles before review")
        if cls._is_stale(db, timeline, active):
            raise HTTPException(status_code=409, detail="Subtitle timing is stale for the current timeline/source text. Regenerate before review.")
        mode = str(render_mode or "OFF").upper()
        if mode not in ("OFF", "BURN_IN"):
            raise HTTPException(status_code=400, detail="render_mode must be OFF or BURN_IN")

        history = state.get("history", [])
        history.append(active)
        reviewed = {
            **active,
            "id": str(uuid.uuid4()),
            "version_number": int(active.get("version_number", 1)) + 1,
            "enabled": bool(enabled),
            "render_mode": mode,
            "review_status": "REVIEWED",
            "is_reviewed": True,
            "created_at": utc_now_iso(),
            "reviewed_at": utc_now_iso(),
        }
        cls._store_state(db, timeline, {"active": reviewed, "history": history})
        return cls._read_track(db, timeline, reviewed)

    @classmethod
    def export_srt(cls, db: Session, project_id: uuid.UUID, timeline_id: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
        timeline = cls._resolve_timeline(db, project_id, timeline_id)
        active = cls._state(timeline).get("active")
        if not active:
            raise HTTPException(status_code=404, detail="No subtitle track found")
        if cls._is_stale(db, timeline, active):
            raise HTTPException(status_code=409, detail="Subtitle timing is stale. Regenerate before export.")
        return str(active.get("srt_content") or ""), {
            "track_id": str(active.get("id")),
            "timeline_version": str(timeline.version),
            "sha256": str(active.get("srt_sha256")),
        }

    @classmethod
    def get_render_snapshot(cls, db: Session, project_id: uuid.UUID, timeline: AssemblyTimeline) -> Dict[str, Any]:
        active = cls._state(timeline).get("active")
        if not active or not bool(active.get("enabled", True)) or str(active.get("render_mode", "OFF")).upper() == "OFF":
            return {"mode": "OFF"}
        if not bool(active.get("is_reviewed", False)):
            raise HTTPException(status_code=400, detail="Burn-in subtitles must be reviewed before render submission")
        if cls._is_stale(db, timeline, active):
            raise HTTPException(status_code=409, detail="Burn-in subtitles are stale. Regenerate and review before rendering.")
        return {
            "mode": "BURN_IN",
            "track_id": str(active.get("id")),
            "timeline_version": int(timeline.version),
            "timeline_fingerprint": str(active.get("timeline_fingerprint")),
            "srt_sha256": str(active.get("srt_sha256")),
            "language": str(active.get("language") or "und"),
        }

    @classmethod
    def materialize_render_srt(
        cls,
        db: Session,
        timeline: AssemblyTimeline,
        snapshot: Dict[str, Any],
    ) -> Optional[str]:
        if str(snapshot.get("mode", "OFF")).upper() != "BURN_IN":
            return None
        active = cls._state(timeline).get("active")
        if not active:
            raise RuntimeError("Burn-in subtitle snapshot references a missing active subtitle track")
        if str(active.get("id")) != str(snapshot.get("track_id")):
            raise RuntimeError("Burn-in subtitle track changed after render submission; fail closed")
        if str(active.get("srt_sha256")) != str(snapshot.get("srt_sha256")):
            raise RuntimeError("Burn-in subtitle SRT checksum changed after render submission; fail closed")
        if cls._is_stale(db, timeline, active):
            raise RuntimeError("Burn-in subtitle track became stale after render submission; fail closed")
        return str(active.get("srt_content") or "")
