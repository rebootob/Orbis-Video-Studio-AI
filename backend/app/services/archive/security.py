"""Security validator for .orbis archive packages.

Prevents ZIP Slip, path traversal, decompression bombs, symlink attacks,
duplicate path collisions, and unauthorized archive payloads.
"""
import os
import re
import stat
import zipfile
from typing import Set

from app.services.archive.constants import (
    MAX_ARCHIVE_BYTES,
    MAX_UNCOMPRESSED_BYTES,
    MAX_FILE_COUNT,
    MAX_COMPRESSION_RATIO,
    ALLOWED_ASSET_EXTENSIONS,
)


class ArchiveSecurityError(Exception):
    """Raised when an archive violates security constraints."""
    pass


class ArchiveSecurityValidator:
    """Validates archive container integrity and security before extraction."""

    @classmethod
    def validate_magic_bytes(cls, archive_path: str) -> None:
        """Verify standard ZIP container magic signature."""
        if not os.path.exists(archive_path):
            raise ArchiveSecurityError("Archive file does not exist")

        file_size = os.path.getsize(archive_path)
        if file_size > MAX_ARCHIVE_BYTES:
            raise ArchiveSecurityError(
                f"Archive exceeds maximum size limit ({file_size} > {MAX_ARCHIVE_BYTES} bytes)"
            )
        if file_size < 4:
            raise ArchiveSecurityError("Archive file is corrupted or too small")

        with open(archive_path, "rb") as f:
            magic = f.read(4)
            if magic != b"PK\x03\x04":
                raise ArchiveSecurityError("Invalid archive signature (not a valid PK ZIP container)")

    @classmethod
    def inspect_archive(cls, archive_path: str) -> zipfile.ZipFile:
        """Inspects archive members for path safety, symlinks, and compression limits.

        Returns an open ZipFile instance if validation passes.
        """
        cls.validate_magic_bytes(archive_path)

        try:
            zf = zipfile.ZipFile(archive_path, "r")
        except zipfile.BadZipFile as e:
            raise ArchiveSecurityError(f"Corrupted or invalid ZIP container: {str(e)}") from e

        entries = zf.infolist()
        if len(entries) > MAX_FILE_COUNT:
            zf.close()
            raise ArchiveSecurityError(
                f"Archive contains excessive file entries ({len(entries)} > {MAX_FILE_COUNT})"
            )

        total_uncompressed = 0
        seen_paths: Set[str] = set()

        for info in entries:
            raw_name = info.filename

            # 1. Backslash rejection: POSIX paths strictly require "/"
            if "\\" in raw_name:
                zf.close()
                raise ArchiveSecurityError(
                    f"Invalid path delimiter: backslashes are strictly prohibited ('{raw_name}')"
                )

            # 2. Leading slash rejection
            if raw_name.startswith("/"):
                zf.close()
                raise ArchiveSecurityError(
                    f"Absolute paths with leading slash are prohibited ('{raw_name}')"
                )

            # 3. Windows drive-letter rejection (e.g. C: or C:/)
            if re.match(r"^[a-zA-Z]:", raw_name):
                zf.close()
                raise ArchiveSecurityError(
                    f"Drive-letter paths are prohibited ('{raw_name}')"
                )

            # 4. UNC path prefix rejection
            if raw_name.startswith("//") or raw_name.startswith("\\\\"):
                zf.close()
                raise ArchiveSecurityError(
                    f"UNC network paths are prohibited ('{raw_name}')"
                )

            # 5. Traversal and empty segment analysis
            segments = raw_name.split("/")
            # Allow trailing empty segment only if entry is explicitly a directory
            for i, seg in enumerate(segments):
                if seg in (".", ".."):
                    zf.close()
                    raise ArchiveSecurityError(
                        f"Directory traversal segment '{seg}' detected in path ('{raw_name}')"
                    )
                if seg == "" and i != len(segments) - 1:
                    zf.close()
                    raise ArchiveSecurityError(
                        f"Empty/consecutive slash segment detected in path ('{raw_name}')"
                    )

            # 6. Duplicate archive member path check
            normalized_name = "/".join(segments).rstrip("/")
            if normalized_name in seen_paths:
                zf.close()
                raise ArchiveSecurityError(
                    f"Duplicate archive member path detected: '{normalized_name}'"
                )
            seen_paths.add(normalized_name)

            # 7. Symlink, hardlink, FIFO, socket, device node rejection
            mode = info.external_attr >> 16
            if mode != 0:
                if stat.S_ISLNK(mode):
                    zf.close()
                    raise ArchiveSecurityError(
                        f"Symlinks are strictly prohibited in archive ('{raw_name}')"
                    )
                if stat.S_ISFIFO(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISSOCK(mode):
                    zf.close()
                    raise ArchiveSecurityError(
                        f"Special device or FIFO nodes are prohibited in archive ('{raw_name}')"
                    )

            # 8. Asset file extension validation
            if raw_name.startswith("assets/") and not raw_name.endswith("/"):
                ext = os.path.splitext(raw_name)[1].lower()
                if ext not in ALLOWED_ASSET_EXTENSIONS:
                    zf.close()
                    raise ArchiveSecurityError(
                        f"Forbidden file extension '{ext}' in asset member ('{raw_name}'). "
                        f"Allowed: {sorted(list(ALLOWED_ASSET_EXTENSIONS))}"
                    )

            # 9. Decompression bomb / compression ratio checks
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                zf.close()
                raise ArchiveSecurityError(
                    f"Total uncompressed archive size exceeds limit ({total_uncompressed} > {MAX_UNCOMPRESSED_BYTES} bytes)"
                )

            # Per-file compression ratio check for files >= 1KB
            if info.file_size > 1024 and info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > MAX_COMPRESSION_RATIO:
                    zf.close()
                    raise ArchiveSecurityError(
                        f"Potential decompression bomb: '{raw_name}' expansion ratio {ratio:.1f}:1 exceeds limit {MAX_COMPRESSION_RATIO}:1"
                    )

        return zf

    @classmethod
    def resolve_safe_extraction_path(cls, sandbox_dir: str, member_path: str) -> str:
        """Resolves target path within sandbox and enforces containment."""
        sandbox_real = os.path.realpath(sandbox_dir)
        target = os.path.realpath(os.path.join(sandbox_real, member_path))

        common = os.path.commonpath([sandbox_real, target])
        if common != sandbox_real:
            raise ArchiveSecurityError(
                f"Path traversal escape detected: target '{target}' is outside sandbox '{sandbox_real}'"
            )
        return target
