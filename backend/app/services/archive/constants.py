"""Constants and limits for .orbis archive packages."""

ARCHIVE_FORMAT_VERSION = "1.0.0"
SUPPORTED_MAJOR_VERSIONS = {1}
SCHEMA_VERSION = "1.0.0"

MAX_ARCHIVE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
MAX_UNCOMPRESSED_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
MAX_FILE_COUNT = 50000
MAX_COMPRESSION_RATIO = 10.0

ALLOWED_ASSET_EXTENSIONS = {
    ".mp4", ".mov", ".png", ".jpg", ".jpeg", ".webp",
    ".wav", ".mp3", ".pdf", ".docx", ".pptx", ".txt", ".json"
}
