import uuid
from app.models.project import Project
from app.models.story import Story
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.generation_job import GenerationJob


def test_domain_models_creation_and_relationships(db_session):
    # 1. Create Project
    project = Project(
        title="Test Sci-Fi Film",
        description="A story about space exploration",
        status="DRAFT",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    assert isinstance(project.id, uuid.UUID)
    assert project.title == "Test Sci-Fi Film"
    assert project.status == "DRAFT"

    # 2. Create Story for Project
    story = Story(
        project_id=project.id,
        logline="Astronaut discovers alien artifact.",
        synopsis="Full synopsis of space adventure.",
        status="DRAFT",
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    assert story.project_id == project.id
    assert project.story.logline == "Astronaut discovers alien artifact."

    # 3. Create Scene for Story
    scene = Scene(
        story_id=story.id,
        scene_number=1,
        heading="INT. SPACESHIP COCKPIT - DAY",
        description="Alarms blare as ship enters orbit.",
        is_locked=False,
    )
    db_session.add(scene)
    db_session.commit()
    db_session.refresh(scene)

    assert scene.story_id == story.id
    assert len(story.scenes) == 1
    assert story.scenes[0].scene_number == 1

    # 4. Create Shot for Scene
    shot = Shot(
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="Close up shot of pilot clutching control stick",
        duration_seconds=5.0,
        is_locked=False,
        status="PENDING",
    )
    db_session.add(shot)
    db_session.commit()
    db_session.refresh(shot)

    assert shot.scene_id == scene.id
    assert len(scene.shots) == 1
    assert scene.shots[0].duration_seconds == 5.0

    # 5. Create Asset for Project
    asset = Asset(
        project_id=project.id,
        name="Hero Pilot Character Turnaround",
        asset_type="CHARACTER",
        storage_path="references/hero_pilot.png",
        media_url="https://storage.orbis.ai/references/hero_pilot.png",
        is_locked=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    assert asset.project_id == project.id
    assert len(project.assets) == 1
    assert project.assets[0].is_locked is True

    # 6. Create GenerationJob for Shot
    job = GenerationJob(
        shot_id=shot.id,
        provider_name="vidu",
        provider_job_id="vidu_job_12345",
        status="PENDING",
        idempotency_key="idem_key_abc123",
        cost_usd=0.50,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.shot_id == shot.id
    assert len(shot.generation_jobs) == 1
    assert shot.generation_jobs[0].provider_name == "vidu"
    assert shot.generation_jobs[0].cost_usd == 0.50
