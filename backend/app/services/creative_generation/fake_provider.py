import time
from typing import Optional, List
from app.services.creative_generation.base import (
    CreativeGenerationProvider,
    CreativeGenerationError,
    GenerationRequestOptions,
    GeneratedStoryDTO,
    GeneratedSceneDTO,
    GeneratedShotDTO,
    ProviderGenerationResult,
)


class FakeCreativeGenerationProvider(CreativeGenerationProvider):
    """Deterministic test double for CreativeGenerationProvider requiring zero external network calls."""

    def __init__(
        self,
        should_fail: bool = False,
        error_code: str = "GENERATION_FAILED",
        error_message: str = "Fake provider failure simulated.",
        simulated_delay_ms: float = 10.0,
    ):
        self.should_fail = should_fail
        self.error_code = error_code
        self.error_message = error_message
        self.simulated_delay_ms = simulated_delay_ms

    def generate_story(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        if self.should_fail:
            raise CreativeGenerationError(self.error_code, self.error_message)

        # Default structured story payload with Thai & English script content
        story = GeneratedStoryDTO(
            title="บทภาพยนตร์จำลอง: การผจญภัยในอวกาศ (Cyberpunk Space Brief)",
            logline="กัปตันซาร่า นำลูกเรือออกสำรวจสถานีอวกาศลึกลับเพื่อตามหาแหล่งพลังงานใหม่",
            synopsis="ในยุคอนาคต สถานีอวกาศ Jupiter Prime ขาดการติดต่อ กัปตันซาร่าเดินทางไปตรวจสอบและพบกับเทคโนโลยีลึกลับ",
            tone="cinematic",
            target_duration_seconds=60.0,
            language="th",
            scenes=[
                GeneratedSceneDTO(
                    scene_number=1,
                    title="EXT. JUPITER ORBIT - NIGHT",
                    purpose="Introduce space station atmosphere and vessel arrival",
                    setting="Deep space near Jupiter with blue gas nebulae",
                    duration_seconds=20.0,
                    narration="ในปี 2088 สถานีอวกาศ จูปีเตอร์ ไพรม์ ขาดการติดต่ออย่างเป็นปริศนา...",
                    dialogue=[{"speaker": "SARA", "text": "เตรียมตัวเข้าสู่รัศมีสถานีอวกาศ"}],
                    shots=[
                        GeneratedShotDTO(
                            shot_number=1,
                            description="Wide shot of spaceship approaching massive dark space station",
                            camera="Slow pan right, wide angle lens",
                            subject="Explorer Vessel Alpha",
                            action="Vessel thrusters glow blue against dark Jupiter backdrop",
                            duration_seconds=5.0,
                            image_prompt="Cinematic wide shot of futuristic spaceship approaching massive dark orbital space station near Jupiter, photorealistic 8k",
                            video_prompt="Futuristic spaceship gliding towards orbital space station, blue thruster trail, slow camera pan, cinematic lighting",
                        ),
                        GeneratedShotDTO(
                            shot_number=2,
                            description="Close up of Captain Sara inside cockpit",
                            camera="Close up shot, eye level",
                            subject="Captain Sara",
                            action="Sara adjusts control levers while scanning sensor display",
                            duration_seconds=5.0,
                            image_prompt="Close up of female astronaut in sci-fi suit inside dimly lit spaceship cockpit, neon blue console reflection",
                            video_prompt="Female astronaut operating holographic flight controls, subtle head movement, glowing console screens",
                        ),
                    ],
                )
            ],
        )

        return ProviderGenerationResult(
            provider="fake_openai",
            model="fake-gpt-4o",
            input_character_count=len(prompt),
            output_character_count=500,
            prompt_tokens=150,
            completion_tokens=250,
            duration_ms=self.simulated_delay_ms,
            data=story,
        )

    def generate_scenes(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        if self.should_fail:
            raise CreativeGenerationError(self.error_code, self.error_message)

        scenes = [
            GeneratedSceneDTO(
                scene_number=1,
                title="INT. RESEARCH LAB - DAY",
                purpose="Discover secret energy core",
                setting="High-tech subterranean lab",
                duration_seconds=15.0,
                narration="ซาร่าก้าวเข้าไปในห้องวิจัยที่เงียบสงบ",
                dialogue=[{"speaker": "SARA", "text": "พบพลังงานหลักแล้ว"}],
                shots=[
                    GeneratedShotDTO(
                        shot_number=1,
                        description="Medium shot of Sara examining glowing core",
                        camera="Tracking shot forward",
                        subject="Glowing orb core",
                        action="Orb pulses bright cyan light",
                        duration_seconds=5.0,
                        image_prompt="Medium shot of female scientist standing in front of glowing cyan energy sphere in high tech lab",
                        video_prompt="Cyan energy core pulsing with light as female scientist steps forward, smooth dolly in",
                    )
                ],
            )
        ]

        return ProviderGenerationResult(
            provider="fake_openai",
            model="fake-gpt-4o",
            input_character_count=len(prompt),
            output_character_count=250,
            prompt_tokens=80,
            completion_tokens=120,
            duration_ms=self.simulated_delay_ms,
            data=scenes,
        )

    def generate_shots(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        if self.should_fail:
            raise CreativeGenerationError(self.error_code, self.error_message)

        shots = [
            GeneratedShotDTO(
                shot_number=1,
                description="Extreme close up of laser crystal alignment",
                camera="Macro lens static shot",
                subject="Crystal prism",
                action="Laser beam passes through crystal matrix",
                duration_seconds=4.0,
                image_prompt="Macro photography of glowing crystal prism refracting red laser beam in dark optical laboratory",
                video_prompt="Red laser beam firing through crystal prism causing light spectrum dispersion, high detail macro motion",
            )
        ]

        return ProviderGenerationResult(
            provider="fake_openai",
            model="fake-gpt-4o",
            input_character_count=len(prompt),
            output_character_count=150,
            prompt_tokens=50,
            completion_tokens=80,
            duration_ms=self.simulated_delay_ms,
            data=shots,
        )
