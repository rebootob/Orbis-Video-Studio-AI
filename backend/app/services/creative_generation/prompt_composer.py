from typing import Optional, List, Dict, Any


class StoryPromptComposer:
    """Composes prompts for full Story generation separating Factual Source vs Creative Direction."""

    @staticmethod
    def compose(
        project_title: str,
        project_brief: Optional[str],
        extracted_documents: List[Dict[str, str]],
        target_duration_seconds: float = 60.0,
        tone: str = "cinematic",
        language: str = "th",
        target_audience: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> str:
        prompt_parts = []

        prompt_parts.append("=== SYSTEM / TASK INSTRUCTION ===")
        prompt_parts.append(
            "You are a professional screenplay writer and AI video director. "
            "Your task is to craft a complete, structured story script with numbered scenes and shots."
        )

        prompt_parts.append("\n=== FACTUAL SOURCE MATERIAL (AUTHORITATIVE) ===")
        if extracted_documents:
            for idx, doc in enumerate(extracted_documents, 1):
                filename = doc.get("filename", f"document_{idx}")
                content = doc.get("content", "").strip()
                prompt_parts.append(f"--- Document #{idx}: {filename} ---\n{content}\n")
        else:
            prompt_parts.append("[No uploaded reference documents provided. Rely on project brief below.]")

        prompt_parts.append("\n=== CREATIVE DIRECTION & OBJECTIVES ===")
        prompt_parts.append(f"Project Title: {project_title}")
        if project_brief:
            prompt_parts.append(f"Project Brief / Objective: {project_brief}")
        if target_audience:
            prompt_parts.append(f"Target Audience: {target_audience}")
        prompt_parts.append(f"Target Total Duration: {target_duration_seconds} seconds")
        prompt_parts.append(f"Tone & Style: {tone}")
        prompt_parts.append(f"Primary Output Language: {language}")
        if custom_instructions:
            prompt_parts.append(f"Owner Instructions: {custom_instructions}")

        prompt_parts.append("\n=== CRITICAL GUIDELINES ===")
        prompt_parts.append(
            "1. FACTUAL GROUNDING: Do NOT invent factual claims or specs that contradict the FACTUAL SOURCE MATERIAL.\n"
            "2. STRUCTURED OUTPUT: Return ONLY valid JSON matching the requested Story schema.\n"
            "3. PROMPTS FOR MEDIA: Every shot MUST include explicit `image_prompt` (detailed visual scene setup for static image AI) "
            "and `video_prompt` (motion, camera movement, subject action for video AI like Vidu).\n"
            "4. UNICODE: Maintain native language (e.g. Thai, English) accurately."
        )

        return "\n".join(prompt_parts)


class ScenePromptComposer:
    """Composes prompts for Scene list generation within an existing Story context."""

    @staticmethod
    def compose(
        story_title: str,
        logline: str,
        synopsis: str,
        extracted_documents: List[Dict[str, str]],
        target_duration_seconds: float = 60.0,
        tone: str = "cinematic",
        language: str = "th",
        custom_instructions: Optional[str] = None,
    ) -> str:
        prompt_parts = []

        prompt_parts.append("=== SYSTEM / TASK INSTRUCTION ===")
        prompt_parts.append("Generate detailed scenes and shots for the locked story below.")

        prompt_parts.append("\n=== LOCKED STORY CONTEXT ===")
        prompt_parts.append(f"Title: {story_title}")
        prompt_parts.append(f"Logline: {logline}")
        prompt_parts.append(f"Synopsis: {synopsis}")
        prompt_parts.append(f"Target Duration: {target_duration_seconds} seconds")
        prompt_parts.append(f"Tone: {tone}")
        prompt_parts.append(f"Language: {language}")

        prompt_parts.append("\n=== FACTUAL SOURCE MATERIAL ===")
        if extracted_documents:
            for idx, doc in enumerate(extracted_documents, 1):
                filename = doc.get("filename", f"document_{idx}")
                content = doc.get("content", "").strip()
                prompt_parts.append(f"--- Document #{idx}: {filename} ---\n{content}\n")
        else:
            prompt_parts.append("[No uploaded reference documents.]")

        if custom_instructions:
            prompt_parts.append(f"\n=== CUSTOM INSTRUCTIONS ===\n{custom_instructions}")

        return "\n".join(prompt_parts)


class ShotPromptComposer:
    """Composes prompts for Shot list generation within an existing Scene context."""

    @staticmethod
    def compose(
        scene_heading: str,
        scene_purpose: Optional[str],
        scene_setting: Optional[str],
        narration: Optional[str],
        dialogue: Optional[List[Dict[str, str]]],
        extracted_documents: List[Dict[str, str]],
        target_scene_duration_seconds: float = 15.0,
        custom_instructions: Optional[str] = None,
    ) -> str:
        prompt_parts = []

        prompt_parts.append("=== SYSTEM / TASK INSTRUCTION ===")
        prompt_parts.append("Generate a sequence of shots for the specific scene described below.")

        prompt_parts.append("\n=== TARGET SCENE CONTEXT ===")
        prompt_parts.append(f"Scene Heading: {scene_heading}")
        if scene_purpose:
            prompt_parts.append(f"Purpose: {scene_purpose}")
        if scene_setting:
            prompt_parts.append(f"Setting: {scene_setting}")
        if narration:
            prompt_parts.append(f"Narration: {narration}")
        if dialogue:
            prompt_parts.append(f"Dialogue: {dialogue}")
        prompt_parts.append(f"Target Scene Duration: {target_scene_duration_seconds} seconds")

        prompt_parts.append("\n=== FACTUAL SOURCE MATERIAL ===")
        if extracted_documents:
            for idx, doc in enumerate(extracted_documents, 1):
                filename = doc.get("filename", f"document_{idx}")
                content = doc.get("content", "").strip()
                prompt_parts.append(f"--- Document #{idx}: {filename} ---\n{content}\n")

        if custom_instructions:
            prompt_parts.append(f"\n=== CUSTOM INSTRUCTIONS ===\n{custom_instructions}")

        return "\n".join(prompt_parts)
