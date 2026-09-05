import uuid
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.document_extraction import DocumentExtraction
from app.models.generation_audit import GenerationAuditLog
from app.services.creative_generation.base import (
    CreativeGenerationProvider,
    CreativeGenerationError,
    GenerationRequestOptions,
    GeneratedStoryDTO,
    GeneratedSceneDTO,
    GeneratedShotDTO,
)
from app.services.creative_generation.prompt_composer import (
    StoryPromptComposer,
    ScenePromptComposer,
    ShotPromptComposer,
)


class StoryGenerationService:
    """Core domain service for Story & Screenplay Script generation and persistence."""

    def __init__(self, db: Session, provider: CreativeGenerationProvider):
        self.db = db
        self.provider = provider

    def _gather_document_extractions(self, project_id: uuid.UUID) -> List[Dict[str, str]]:
        """Fetch all completed document extractions for project assets."""
        assets = self.db.query(Asset).filter(
            Asset.project_id == project_id,
            Asset.asset_type == "DOCUMENT",
        ).all()

        extractions: List[Dict[str, str]] = []
        for asset in assets:
            ext = self.db.query(DocumentExtraction).filter(
                DocumentExtraction.asset_id == asset.id,
                DocumentExtraction.status == "SUCCESS",
            ).first()
            if ext and ext.extracted_text and ext.extracted_text.strip():
                extractions.append({
                    "filename": asset.original_filename,
                    "content": ext.extracted_text.strip(),
                })
        return extractions

    def _log_audit(
        self,
        project_id: uuid.UUID,
        request_type: str,
        result: Optional[Any] = None,
        error: Optional[CreativeGenerationError] = None,
        duration_ms: float = 0.0,
        commit: bool = True,
    ) -> GenerationAuditLog:
        """Record generation audit entry in database."""
        audit = GenerationAuditLog(
            id=uuid.uuid4(),
            project_id=project_id,
            provider=getattr(result, "provider", "unknown") if result else "unknown",
            model=getattr(result, "model", "unknown") if result else "unknown",
            request_type=request_type,
            input_character_count=getattr(result, "input_character_count", 0) if result else 0,
            output_character_count=getattr(result, "output_character_count", 0) if result else 0,
            prompt_tokens=getattr(result, "prompt_tokens", None) if result else None,
            completion_tokens=getattr(result, "completion_tokens", None) if result else None,
            duration_ms=duration_ms,
            status="SUCCESS" if not error else "FAILED",
            error_message=error.message if error else None,
        )
        self.db.add(audit)
        if commit:
            self.db.commit()
        return audit

    def generate_project_story(
        self,
        project_id: uuid.UUID,
        target_duration_seconds: float = 60.0,
        tone: str = "cinematic",
        language: str = "th",
        target_audience: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        options: Optional[GenerationRequestOptions] = None,
    ) -> Story:
        """Orchestrates complete Story, Scene, and Shot generation for a Project."""
        # 1. Fetch Project
        project = self.db.get(Project, project_id)
        if not project:
            raise CreativeGenerationError(
                "PROJECT_NOT_FOUND", f"Project with ID '{project_id}' not found."
            )

        # 2. Check existing Story lock state
        existing_story = self.db.query(Story).filter(Story.project_id == project_id).first()
        if existing_story and existing_story.is_locked:
            raise CreativeGenerationError(
                "STORY_LOCKED", f"Story for project '{project_id}' is locked and cannot be regenerated."
            )

        # 3. Gather extracted document facts from WP004
        doc_extractions = self._gather_document_extractions(project_id)

        # 4. NO_SOURCE_CONTEXT Guard: verify at least one source of context is provided
        has_brief = bool(project.description and project.description.strip())
        has_docs = any(d.get("content") and d.get("content").strip() for d in doc_extractions)
        has_custom = bool(custom_instructions and custom_instructions.strip())

        if not (has_brief or has_docs or has_custom):
            raise CreativeGenerationError(
                "NO_SOURCE_CONTEXT",
                "No source context provided for story generation. Provide a project brief, document assets, or custom instructions.",
            )

        # 5. Build locked project reference context
        from app.services.reference_library.context_builder import ReferenceContextBuilder
        ref_context = ReferenceContextBuilder.build_context(self.db, project_id)
        ref_text = ReferenceContextBuilder.format_prompt_section(ref_context)

        # 6. Compose prompt
        prompt = StoryPromptComposer.compose(
            project_title=project.title,
            project_brief=project.description,
            extracted_documents=doc_extractions,
            target_duration_seconds=target_duration_seconds,
            tone=tone,
            language=language,
            target_audience=target_audience,
            custom_instructions=custom_instructions,
            reference_context_text=ref_text,
        )

        # 6. Dispatch call to CreativeGenerationProvider
        start_time = time.perf_counter()
        try:
            res = self.provider.generate_story(prompt=prompt, options=options)
            duration_ms = res.duration_ms
            story_dto: GeneratedStoryDTO = res.data
        except CreativeGenerationError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_audit(
                project_id=project_id,
                request_type="STORY_GENERATE",
                error=e,
                duration_ms=duration_ms,
                commit=True,
            )
            raise e

        # 7. Persist/Update Story, Scenes, Shots, and SUCCESS Audit in single atomic DB transaction
        try:
            self._log_audit(
                project_id=project_id,
                request_type="STORY_GENERATE",
                result=res,
                duration_ms=duration_ms,
                commit=False,
            )

            if existing_story:
                story = existing_story
                story.title = story_dto.title
                story.logline = story_dto.logline
                story.synopsis = story_dto.synopsis
                story.tone = story_dto.tone
                story.target_duration_seconds = story_dto.target_duration_seconds
                story.language = story_dto.language
                story.status = "GENERATED"

                # Remove unlocked old scenes (cascade will remove shots)
                for scene in list(story.scenes):
                    if not scene.is_locked:
                        self.db.delete(scene)
            else:
                story = Story(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    title=story_dto.title,
                    logline=story_dto.logline,
                    synopsis=story_dto.synopsis,
                    tone=story_dto.tone,
                    target_duration_seconds=story_dto.target_duration_seconds,
                    language=story_dto.language,
                    status="GENERATED",
                )
                self.db.add(story)
                self.db.flush()

            # Add generated scenes and shots
            for s_dto in story_dto.scenes:
                scene = Scene(
                    id=uuid.uuid4(),
                    story_id=story.id,
                    scene_number=s_dto.scene_number,
                    heading=s_dto.title,
                    purpose=s_dto.purpose,
                    setting=s_dto.setting,
                    duration_seconds=s_dto.duration_seconds,
                    narration=s_dto.narration,
                    dialogue=s_dto.dialogue,
                )
                self.db.add(scene)
                self.db.flush()

                for sh_dto in s_dto.shots:
                    shot = Shot(
                        id=uuid.uuid4(),
                        scene_id=scene.id,
                        shot_number=sh_dto.shot_number,
                        shot_type="AI_GENERATED",
                        visual_prompt=sh_dto.description,
                        image_prompt=sh_dto.image_prompt,
                        video_prompt=sh_dto.video_prompt,
                        camera=sh_dto.camera,
                        subject=sh_dto.subject,
                        action=sh_dto.action,
                        duration_seconds=sh_dto.duration_seconds,
                        status="PENDING",
                    )
                    self.db.add(shot)

            self.db.commit()
            self.db.refresh(story)
            return story
        except Exception:
            self.db.rollback()
            raise

    def generate_story_scenes(
        self,
        story_id: uuid.UUID,
        custom_instructions: Optional[str] = None,
        options: Optional[GenerationRequestOptions] = None,
    ) -> List[Scene]:
        """Regenerates/Generates scenes for an existing story context."""
        story = self.db.get(Story, story_id)
        if not story:
            raise CreativeGenerationError("STORY_NOT_FOUND", f"Story with ID '{story_id}' not found.")
        if story.is_locked:
            raise CreativeGenerationError("STORY_LOCKED", "Story is locked.")

        doc_extractions = self._gather_document_extractions(story.project_id)

        prompt = ScenePromptComposer.compose(
            story_title=story.title or story.project.title,
            logline=story.logline or "",
            synopsis=story.synopsis or "",
            extracted_documents=doc_extractions,
            target_duration_seconds=story.target_duration_seconds or 60.0,
            tone=story.tone or "cinematic",
            language=story.language or "th",
            custom_instructions=custom_instructions,
        )

        start_time = time.perf_counter()
        try:
            res = self.provider.generate_scenes(prompt=prompt, options=options)
            scenes_dto: List[GeneratedSceneDTO] = res.data
        except CreativeGenerationError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_audit(
                project_id=story.project_id,
                request_type="SCENE_GENERATE",
                error=e,
                duration_ms=duration_ms,
                commit=True,
            )
            raise e

        try:
            self._log_audit(
                project_id=story.project_id,
                request_type="SCENE_GENERATE",
                result=res,
                duration_ms=res.duration_ms,
                commit=False,
            )

            # Remove unlocked scenes
            for scene in list(story.scenes):
                if not scene.is_locked:
                    self.db.delete(scene)

            created_scenes = []
            for s_dto in scenes_dto:
                scene = Scene(
                    id=uuid.uuid4(),
                    story_id=story.id,
                    scene_number=s_dto.scene_number,
                    heading=s_dto.title,
                    purpose=s_dto.purpose,
                    setting=s_dto.setting,
                    duration_seconds=s_dto.duration_seconds,
                    narration=s_dto.narration,
                    dialogue=s_dto.dialogue,
                )
                self.db.add(scene)
                self.db.flush()

                for sh_dto in s_dto.shots:
                    shot = Shot(
                        id=uuid.uuid4(),
                        scene_id=scene.id,
                        shot_number=sh_dto.shot_number,
                        shot_type="AI_GENERATED",
                        visual_prompt=sh_dto.description,
                        image_prompt=sh_dto.image_prompt,
                        video_prompt=sh_dto.video_prompt,
                        camera=sh_dto.camera,
                        subject=sh_dto.subject,
                        action=sh_dto.action,
                        duration_seconds=sh_dto.duration_seconds,
                        status="PENDING",
                    )
                    self.db.add(shot)
                created_scenes.append(scene)

            self.db.commit()
            return created_scenes
        except Exception:
            self.db.rollback()
            raise

    def generate_scene_shots(
        self,
        scene_id: uuid.UUID,
        custom_instructions: Optional[str] = None,
        options: Optional[GenerationRequestOptions] = None,
    ) -> List[Shot]:
        """Regenerates/Generates shots for an existing scene context."""
        scene = self.db.get(Scene, scene_id)
        if not scene:
            raise CreativeGenerationError("SCENE_NOT_FOUND", f"Scene with ID '{scene_id}' not found.")
        if scene.is_locked:
            raise CreativeGenerationError("SCENE_LOCKED", "Scene is locked.")

        doc_extractions = self._gather_document_extractions(scene.story.project_id)

        prompt = ShotPromptComposer.compose(
            scene_heading=scene.heading or f"Scene {scene.scene_number}",
            scene_purpose=scene.purpose,
            scene_setting=scene.setting,
            narration=scene.narration,
            dialogue=scene.dialogue,
            extracted_documents=doc_extractions,
            target_scene_duration_seconds=scene.duration_seconds or 15.0,
            custom_instructions=custom_instructions,
        )

        start_time = time.perf_counter()
        try:
            res = self.provider.generate_shots(prompt=prompt, options=options)
            shots_dto: List[GeneratedShotDTO] = res.data
        except CreativeGenerationError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_audit(
                project_id=scene.story.project_id,
                request_type="SHOT_GENERATE",
                error=e,
                duration_ms=duration_ms,
                commit=True,
            )
            raise e

        try:
            self._log_audit(
                project_id=scene.story.project_id,
                request_type="SHOT_GENERATE",
                result=res,
                duration_ms=res.duration_ms,
                commit=False,
            )

            # Remove unlocked shots
            for shot in list(scene.shots):
                if not shot.is_locked:
                    self.db.delete(shot)

            created_shots = []
            for sh_dto in shots_dto:
                shot = Shot(
                    id=uuid.uuid4(),
                    scene_id=scene.id,
                    shot_number=sh_dto.shot_number,
                    shot_type="AI_GENERATED",
                    visual_prompt=sh_dto.description,
                    image_prompt=sh_dto.image_prompt,
                    video_prompt=sh_dto.video_prompt,
                    camera=sh_dto.camera,
                    subject=sh_dto.subject,
                    action=sh_dto.action,
                    duration_seconds=sh_dto.duration_seconds,
                    status="PENDING",
                )
                self.db.add(shot)
                created_shots.append(shot)

            self.db.commit()
            return created_shots
        except Exception:
            self.db.rollback()
            raise
