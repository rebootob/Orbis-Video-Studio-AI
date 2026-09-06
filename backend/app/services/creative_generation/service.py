import uuid
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.story import Story, utc_now
from app.models.story_version import StoryVersion
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
        if result and not error:
            try:
                from app.services.cost_ledger import CostLedgerService
                from app.services.pricing import ProviderPricingService, CostStatus
                cost, curr, _ = ProviderPricingService.estimate_cost(
                    provider=getattr(result, "provider", "openai"),
                    operation="STORY_GENERATION",
                    model=getattr(result, "model", "gpt-4o"),
                    params={
                        "prompt_tokens": getattr(result, "prompt_tokens", None) or 0,
                        "completion_tokens": getattr(result, "completion_tokens", None) or 0,
                    },
                )
                CostLedgerService.record_entry(
                    self.db,
                    project_id=project_id,
                    provider=getattr(result, "provider", "openai"),
                    operation=f"STORY_{request_type}",
                    model=getattr(result, "model", "gpt-4o"),
                    usage_units={
                        "prompt_tokens": getattr(result, "prompt_tokens", None),
                        "completion_tokens": getattr(result, "completion_tokens", None),
                        "duration_ms": duration_ms,
                    },
                    estimated_cost=cost,
                    actual_cost=cost,
                    currency=curr,
                    cost_status=CostStatus.CONFIRMED if cost is not None else CostStatus.UNKNOWN,
                    commit=False,
                )
            except Exception as exc:
                audit.status = "ACCOUNTING_FAILED"
                audit.error_message = f"Usage ledger recording failed: {exc}"
                self.db.commit()
                raise CreativeGenerationError(
                    "LEDGER_RECORDING_FAILED", f"Usage ledger recording failed: {exc}"
                ) from exc

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
        generate_scenes: bool = False,
    ) -> Story:
        """Orchestrates complete Story generation for a Project, optionally generating scenes and shots."""
        # 1. Fetch Project
        project = self.db.get(Project, project_id)
        if not project:
            raise CreativeGenerationError(
                "PROJECT_NOT_FOUND", f"Project '{project_id}' not found."
            )

        # 2. Check Project Lock
        if getattr(project, "is_locked", False):
            raise CreativeGenerationError(
                "PROJECT_LOCKED", f"Project '{project_id}' is locked against modification."
            )

        # 3. Check Existing Story Lock
        existing_story = self.db.query(Story).filter(Story.project_id == project_id).first()
        if existing_story and existing_story.is_locked:
            raise CreativeGenerationError(
                "STORY_LOCKED", f"Story for project '{project_id}' is locked against regeneration."
            )

        # 4. Gather extracted document facts from WP004
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

        # 6. Compose Prompt
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

        # Check budget before dispatch, factoring in estimated cost if pricing is configured
        from app.services.budget import BudgetService
        from app.services.pricing import ProviderPricingService
        model_name = (getattr(options, "model_override", None) or getattr(options, "model", None)) or "gpt-4o"
        est_cost, _, _ = ProviderPricingService.estimate_cost(
            provider="openai",
            operation="STORY_GENERATION",
            model=model_name,
            params={
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": 1000,
            },
        )
        try:
            BudgetService.check_budget_before_dispatch(self.db, project_id, estimated_cost=est_cost)
        except Exception as exc:
            raise CreativeGenerationError(
                "BUDGET_EXCEEDED", str(exc.detail if hasattr(exc, "detail") else exc)
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
                # Retain full history: Snapshot previous Story revision before overwriting
                prev_version = getattr(story, "version_number", 1) or 1
                snapshot = StoryVersion(
                    id=uuid.uuid4(),
                    story_id=story.id,
                    project_id=project_id,
                    version_number=prev_version,
                    title=story.title,
                    logline=story.logline,
                    synopsis=story.synopsis,
                    tone=story.tone,
                    target_duration_seconds=story.target_duration_seconds,
                    language=story.language,
                    status="SUPERSEDED",
                    created_at=story.updated_at or utc_now(),
                )
                self.db.add(snapshot)
                self.db.flush()

                story.version_number = prev_version + 1
                story.title = story_dto.title
                story.logline = story_dto.logline
                story.synopsis = story_dto.synopsis
                story.tone = story_dto.tone
                story.target_duration_seconds = story_dto.target_duration_seconds
                story.language = story_dto.language
                story.status = "GENERATED"

                # Invalidate/supersede downstream storyboard & shots when upstream story outline changes
                for scene in list(story.scenes):
                    if not scene.is_locked:
                        scene.scene_config = dict(scene.scene_config or {})
                        scene.scene_config["archived"] = True
                        for shot in scene.shots:
                            if not shot.is_locked:
                                shot.status = "ARCHIVED"
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
                    version_number=1,
                )
                self.db.add(story)
                self.db.flush()

            # Add generated scenes and shots only when generate_scenes is True
            if generate_scenes:
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
        except CreativeGenerationError:
            raise
        except Exception:
            self.db.rollback()
            raise

    def generate_story_scenes(
        self,
        story_id: uuid.UUID,
        custom_instructions: Optional[str] = None,
        options: Optional[GenerationRequestOptions] = None,
        generate_shots: bool = False,
    ) -> List[Scene]:
        """Regenerates/Generates scenes for an existing story context with history retention."""
        story = self.db.get(Story, story_id)
        if not story:
            raise CreativeGenerationError("STORY_NOT_FOUND", f"Story with ID '{story_id}' not found.")
        if story.is_locked:
            raise CreativeGenerationError("STORY_LOCKED", "Story is locked.")

        # Gate enforcement for STORY mode:
        project = self.db.get(Project, story.project_id)
        if project and project.video_mode == "STORY":
            ALLOWED_STORYBOARD_STORY_STATUSES = {
                "STORY_APPROVED",
                "STORYBOARD_GENERATED",
                "STORYBOARD_APPROVED",
                "SHOT_PLAN_GENERATED",
                "SHOT_PLAN_APPROVED",
                "IMAGES_GENERATED",
                "VIDEO_IN_PROGRESS",
                "READY_FOR_REVIEW",
                "COMPLETED",
            }
            if story.status != "APPROVED" and project.status not in ALLOWED_STORYBOARD_STORY_STATUSES:
                raise CreativeGenerationError(
                    "STAGE_NOT_APPROVED",
                    f"Storyboard generation in STORY mode requires 'STORY_APPROVED' stage, current project status is '{project.status}'."
                )

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

        # Check budget before dispatch, factoring in estimated cost if pricing is configured
        from app.services.budget import BudgetService
        from app.services.pricing import ProviderPricingService
        model_name = (getattr(options, "model_override", None) or getattr(options, "model", None)) or "gpt-4o"
        est_cost, _, _ = ProviderPricingService.estimate_cost(
            provider="openai",
            operation="STORY_GENERATION",
            model=model_name,
            params={
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": 500,
            },
        )
        try:
            BudgetService.check_budget_before_dispatch(self.db, story.project_id, estimated_cost=est_cost)
        except Exception as exc:
            raise CreativeGenerationError(
                "BUDGET_EXCEEDED", str(exc.detail if hasattr(exc, "detail") else exc)
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

            # Soft-archive unlocked scenes and shots to retain full history and lineage
            for scene in list(story.scenes):
                if not scene.is_locked:
                    scene.scene_config = dict(scene.scene_config or {})
                    scene.scene_config["archived"] = True
                    for shot in scene.shots:
                        if not shot.is_locked:
                            shot.status = "ARCHIVED"

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

                if generate_shots:
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
        except CreativeGenerationError:
            raise
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

        project_id = scene.project_id or (scene.story.project_id if scene.story else None)
        project = self.db.get(Project, project_id) if project_id else None
        if project:
            ALLOWED_SHOT_PLAN_STATUSES = {
                "STORYBOARD_APPROVED",
                "SHOT_PLAN_GENERATED",
                "SHOT_PLAN_APPROVED",
                "IMAGES_GENERATED",
                "VIDEO_IN_PROGRESS",
                "READY_FOR_REVIEW",
                "COMPLETED",
            }
            if project.status not in ALLOWED_SHOT_PLAN_STATUSES:
                raise CreativeGenerationError(
                    "STAGE_NOT_APPROVED",
                    f"Shot Plan generation requires 'STORYBOARD_APPROVED' stage, current project status is '{project.status}'."
                )

        doc_extractions = self._gather_document_extractions(project_id) if project_id else []

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

        if project_id:
            from app.services.budget import BudgetService
            from app.services.pricing import ProviderPricingService
            model_name = (getattr(options, "model_override", None) or getattr(options, "model", None)) or "gpt-4o"
            est_cost, _, _ = ProviderPricingService.estimate_cost(
                provider="openai",
                operation="STORY_GENERATION",
                model=model_name,
                params={
                    "prompt_tokens": max(1, len(prompt) // 4),
                    "completion_tokens": 500,
                },
            )
            try:
                BudgetService.check_budget_before_dispatch(self.db, project_id, estimated_cost=est_cost)
            except Exception as exc:
                raise CreativeGenerationError(
                    "BUDGET_EXCEEDED", str(exc.detail if hasattr(exc, "detail") else exc)
                )

        start_time = time.perf_counter()
        try:
            res = self.provider.generate_shots(prompt=prompt, options=options)
            shots_dto: List[GeneratedShotDTO] = res.data
        except CreativeGenerationError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_audit(
                project_id=project_id,
                request_type="SHOT_GENERATE",
                error=e,
                duration_ms=duration_ms,
                commit=True,
            )
            raise e

        try:
            self._log_audit(
                project_id=project_id,
                request_type="SHOT_GENERATE",
                result=res,
                duration_ms=res.duration_ms,
                commit=False,
            )

            # Soft-archive unlocked old shots to preserve history and lineage
            for shot in list(scene.shots):
                if not shot.is_locked:
                    shot.status = "ARCHIVED"

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
        except CreativeGenerationError:
            raise
        except Exception:
            self.db.rollback()
            raise

    def generate_project_storyboard(
        self,
        project_id: uuid.UUID,
        custom_instructions: Optional[str] = None,
        options: Optional[GenerationRequestOptions] = None,
        generate_shots: bool = False,
    ) -> List[Scene]:
        """Generates storyboard scenes directly for a project (for SHORT, LOOP, SCENE modes bypassing Story)."""
        project = self.db.get(Project, project_id)
        if not project:
            raise CreativeGenerationError("PROJECT_NOT_FOUND", f"Project with ID '{project_id}' not found.")
        if getattr(project, "is_locked", False):
            raise CreativeGenerationError("PROJECT_LOCKED", "Project is locked.")

        # If in STORY mode, must have a Story and delegate to generate_story_scenes (which enforces STORY_APPROVED)
        if project.video_mode == "STORY":
            if not project.story:
                raise CreativeGenerationError(
                    "STAGE_NOT_APPROVED",
                    "Storyboard generation in STORY mode requires an approved Story outline first.",
                )
            return self.generate_story_scenes(
                story_id=project.story.id,
                custom_instructions=custom_instructions,
                options=options,
                generate_shots=generate_shots,
            )

        # For non-STORY modes, if project happens to have an existing story context, delegate
        if project.story:
            return self.generate_story_scenes(
                story_id=project.story.id,
                custom_instructions=custom_instructions,
                options=options,
                generate_shots=generate_shots,
            )

        doc_extractions = self._gather_document_extractions(project_id)

        prompt = ScenePromptComposer.compose(
            story_title=project.title,
            logline=project.description or f"{project.video_mode} project",
            synopsis=project.description or f"{project.video_mode} production layout",
            extracted_documents=doc_extractions,
            target_duration_seconds=project.target_duration_seconds or 30.0,
            tone="cinematic",
            language="th",
            custom_instructions=custom_instructions,
        )

        from app.services.budget import BudgetService
        from app.services.pricing import ProviderPricingService
        model_name = (getattr(options, "model_override", None) or getattr(options, "model", None)) or "gpt-4o"
        est_cost, _, _ = ProviderPricingService.estimate_cost(
            provider="openai",
            operation="STORY_GENERATION",
            model=model_name,
            params={
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": 500,
            },
        )
        try:
            BudgetService.check_budget_before_dispatch(self.db, project_id, estimated_cost=est_cost)
        except Exception as exc:
            raise CreativeGenerationError(
                "BUDGET_EXCEEDED", str(exc.detail if hasattr(exc, "detail") else exc)
            )

        start_time = time.perf_counter()
        try:
            res = self.provider.generate_scenes(prompt=prompt, options=options)
            scenes_dto: List[GeneratedSceneDTO] = res.data
        except CreativeGenerationError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_audit(
                project_id=project_id,
                request_type="SCENE_GENERATE",
                error=e,
                duration_ms=duration_ms,
                commit=True,
            )
            raise e

        try:
            self._log_audit(
                project_id=project_id,
                request_type="SCENE_GENERATE",
                result=res,
                duration_ms=res.duration_ms,
                commit=False,
            )

            # Soft-archive unlocked scenes directly associated with project
            existing_scenes = self.db.query(Scene).filter(Scene.project_id == project_id).all()
            for scene in existing_scenes:
                if not scene.is_locked:
                    scene.scene_config = dict(scene.scene_config or {})
                    scene.scene_config["archived"] = True
                    for shot in scene.shots:
                        if not shot.is_locked:
                            shot.status = "ARCHIVED"

            created_scenes = []
            for s_dto in scenes_dto:
                scene = Scene(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    story_id=None,
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

                if generate_shots:
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
        except CreativeGenerationError:
            raise
        except Exception:
            self.db.rollback()
            raise
