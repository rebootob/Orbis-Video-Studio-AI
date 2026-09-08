import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


from app.services.storage.mock import InMemoryObjectStorageProvider
from app.services.storage.factory import get_storage_provider, set_storage_provider_override


@pytest.fixture
def mock_storage() -> InMemoryObjectStorageProvider:
    return InMemoryObjectStorageProvider()


@pytest.fixture(autouse=True)
def configure_test_storage(mock_storage: InMemoryObjectStorageProvider):
    set_storage_provider_override(mock_storage)
    yield mock_storage
    set_storage_provider_override(None)


@pytest.fixture(autouse=True)
def configure_test_image_provider():
    """Production defaults stay real; tests explicitly route deterministic image work to mock."""
    previous = settings.DEFAULT_IMAGE_PROVIDER
    settings.DEFAULT_IMAGE_PROVIDER = "mock_image"
    yield
    settings.DEFAULT_IMAGE_PROVIDER = previous


@pytest.fixture(autouse=True)
def configure_test_audio_provider():
    """Production defaults stay real; tests explicitly route deterministic audio work to mock."""
    from app.providers.audio.factory import AudioProviderFactory

    previous = settings.DEFAULT_AUDIO_PROVIDER
    settings.DEFAULT_AUDIO_PROVIDER = "mock_audio"
    AudioProviderFactory.reset_default_provider_name()
    yield
    settings.DEFAULT_AUDIO_PROVIDER = previous
    AudioProviderFactory.reset_default_provider_name()


@pytest.fixture
def client(db_session: Session, mock_storage: InMemoryObjectStorageProvider) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_storage():
        return mock_storage

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_storage_provider] = override_get_storage

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
