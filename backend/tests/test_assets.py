import io
import uuid
import hashlib
import pytest
from app.models.project import Project
from app.models.asset import Asset
from app.services.storage.mock import InMemoryObjectStorageProvider


def test_storage_provider_interface_behavior():
    provider = InMemoryObjectStorageProvider()
    bucket = "test-bucket"
    key = "test/path/file.txt"
    content = b"Hello, Object Storage!"

    # 1. Put object
    ret_key = provider.put_object(bucket, key, content, content_type="text/plain")
    assert ret_key == key
    assert provider.object_exists(bucket, key) is True

    # 2. Get object
    retrieved = provider.get_object(bucket, key)
    assert retrieved == content

    # 3. Presigned URL
    url = provider.generate_presigned_url(bucket, key)
    assert "mock-storage.local" in url
    assert key in url

    # 4. Delete object
    deleted = provider.delete_object(bucket, key)
    assert deleted is True
    assert provider.object_exists(bucket, key) is False


def test_asset_upload_and_metadata_retrieval(client, db_session, mock_storage):
    # Create test project
    project = Project(title="Asset Test Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    file_content = b"Sample script file payload"
    expected_checksum = hashlib.sha256(file_content).hexdigest()

    # Upload file
    response = client.post(
        "/api/v1/assets/upload",
        data={
            "project_id": str(project.id),
            "name": "Project Brief Document",
            "asset_type": "DOCUMENT",
        },
        files={"file": ("script_v1.txt", io.BytesIO(file_content), "text/plain")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Project Brief Document"
    assert data["original_filename"] == "script_v1.txt"
    assert data["asset_type"] == "DOCUMENT"
    assert data["content_type"] == "text/plain"
    assert data["file_size_bytes"] == len(file_content)
    assert data["checksum_sha256"] == expected_checksum
    assert data["download_url"] is not None
    assert f"projects/{project.id}/assets/" in data["storage_key"]

    asset_id = data["id"]

    # Retrieve metadata GET /api/v1/assets/{asset_id}
    get_resp = client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == asset_id
    assert get_data["checksum_sha256"] == expected_checksum


def test_asset_download_url(client, db_session, mock_storage):
    project = Project(title="Download Test Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    file_content = b"Test image content"
    upload_resp = client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id), "asset_type": "IMAGE"},
        files={"file": ("reference.png", io.BytesIO(file_content), "image/png")},
    )
    asset_id = upload_resp.json()["id"]

    # Get download access GET /api/v1/assets/{asset_id}/download
    dl_resp = client.get(f"/api/v1/assets/{asset_id}/download")
    assert dl_resp.status_code == 200
    dl_data = dl_resp.json()
    assert dl_data["asset_id"] == asset_id
    assert "download_url" in dl_data
    assert dl_data["expires_in"] == 3600


def test_list_project_assets(client, db_session):
    project = Project(title="Multi Asset Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # Upload 2 assets
    client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id)},
        files={"file": ("file1.txt", io.BytesIO(b"content 1"), "text/plain")},
    )
    client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id)},
        files={"file": ("file2.txt", io.BytesIO(b"content 2"), "text/plain")},
    )

    list_resp = client.get(f"/api/v1/projects/{project.id}/assets")
    assert list_resp.status_code == 200
    assets = list_resp.json()
    assert len(assets) == 2


def test_asset_deletion(client, db_session, mock_storage):
    project = Project(title="Deletion Test Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    file_content = b"Temporary file"
    upload_resp = client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id)},
        files={"file": ("temp.txt", io.BytesIO(file_content), "text/plain")},
    )
    asset_id = upload_resp.json()["id"]
    storage_key = upload_resp.json()["storage_key"]
    bucket = upload_resp.json()["storage_bucket"]

    assert mock_storage.object_exists(bucket, storage_key) is True

    # Delete asset
    del_resp = client.delete(f"/api/v1/assets/{asset_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Confirm deleted from DB and storage
    get_resp = client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 404
    assert mock_storage.object_exists(bucket, storage_key) is False


def test_asset_deletion_failure_preserves_db_record(client, db_session, mock_storage):
    project = Project(title="Deletion Fail Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    upload_resp = client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id)},
        files={"file": ("critical.txt", io.BytesIO(b"critical payload"), "text/plain")},
    )
    asset_id = upload_resp.json()["id"]

    # Simulate storage error
    mock_storage.simulate_deletion_failure = True

    del_resp = client.delete(f"/api/v1/assets/{asset_id}")
    assert del_resp.status_code == 500

    # Verify DB record is preserved
    mock_storage.simulate_deletion_failure = False
    get_resp = client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 200


def test_asset_upload_validations(client, db_session):
    project = Project(title="Validation Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    # 1. Non-existent project
    fake_project_id = str(uuid.uuid4())
    resp1 = client.post(
        "/api/v1/assets/upload",
        data={"project_id": fake_project_id},
        files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert resp1.status_code == 404

    # 2. Empty file
    resp2 = client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id)},
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert resp2.status_code == 400
    assert "empty" in resp2.json()["detail"].lower()


def test_path_traversal_sanitization(client, db_session):
    project = Project(title="Path Safety Project", status="DRAFT")
    db_session.add(project)
    db_session.commit()

    resp = client.post(
        "/api/v1/assets/upload",
        data={"project_id": str(project.id)},
        files={"file": ("../../../../etc/passwd", io.BytesIO(b"root:x:0:0"), "text/plain")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert ".." not in data["storage_key"]
    assert "passwd" in data["storage_key"]
    assert data["original_filename"] == "passwd"
