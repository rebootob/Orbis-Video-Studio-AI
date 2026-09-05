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
        original_filename="hero_pilot.png",
        asset_type="CHARACTER",
        content_type="image/png",
        file_size_bytes=1024,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_bucket="orbis-assets",
        storage_key="projects/123/assets/hero_pilot.png",
        is_locked=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    assert asset.project_id == project.id
    assert len(project.assets) == 1
    assert project.assets[0].is_locked is True
    assert project.assets[0].original_filename == "hero_pilot.png"

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


def test_shot_and_provider_neutrality(db_session):
    project = Project(title="Neutrality Test", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    story = Story(project_id=project.id, logline="Test neutrality", status="DRAFT")
    db_session.add(story)
    db_session.commit()

    scene = Scene(story_id=story.id, scene_number=1, heading="EXT. FIELD - DAY")
    db_session.add(scene)
    db_session.commit()

    # Test imported and hybrid shot types (not defaulting to AI_GENERATED)
    imported_shot = Shot(scene_id=scene.id, shot_number=1, shot_type="IMPORTED", duration_seconds=3.0)
    hybrid_shot = Shot(scene_id=scene.id, shot_number=2, shot_type="HYBRID", duration_seconds=4.0)
    db_session.add_all([imported_shot, hybrid_shot])
    db_session.commit()
    db_session.refresh(imported_shot)
    db_session.refresh(hybrid_shot)

    assert imported_shot.shot_type == "IMPORTED"
    assert hybrid_shot.shot_type == "HYBRID"

    # Test provider-neutral generation jobs (e.g. luma, runway, custom_adapter)
    job_luma = GenerationJob(shot_id=imported_shot.id, provider_name="luma", status="PENDING")
    job_runway = GenerationJob(shot_id=hybrid_shot.id, provider_name="runway", status="COMPLETED")
    db_session.add_all([job_luma, job_runway])
    db_session.commit()
    db_session.refresh(job_luma)
    db_session.refresh(job_runway)

    assert job_luma.provider_name == "luma"
    assert job_runway.provider_name == "runway"

