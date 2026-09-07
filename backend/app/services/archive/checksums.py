"""Checksum calculations and non-circular trust-root verification.

Enforces:
1. Canonical JSON serialization (RFC 8785 / JCS)
2. Non-circular trust root:
   - manifest.json hashes all payload members (excludes itself & checksums.sha256)
   - checksums.sha256 hashes all payload members + manifest.json (excludes itself)
3. Deterministic GNU coreutils format, lexicographically sorted, UNIX LF
"""
import hashlib
import json
import os
from typing import Any, Dict, Tuple


class ChecksumVerificationError(Exception):
    """Base error for checksum failures."""
    pass


class TamperedManifestError(ChecksumVerificationError):
    """Raised when manifest.json does not match the checksum in checksums.sha256."""
    pass


class TamperedPayloadError(ChecksumVerificationError):
    """Raised when a payload file hash does not match checksums.sha256."""
    pass


class ManifestChecksumDiscrepancyError(ChecksumVerificationError):
    """Raised when manifest.json and checksums.sha256 have mismatched entries or hashes."""
    pass


class ArchiveChecksumService:
    """Provides canonical hashing, manifest creation, and trust-root verification."""

    @staticmethod
    def canonical_json_dumps(obj: Any) -> bytes:
        """Serializes Python object to canonical JSON bytes (RFC 8785 / JCS).

        Sorted keys, compact token delimiters, UTF-8 encoded without BOM.
        """
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")

    @staticmethod
    def compute_sha256_file(file_path: str) -> str:
        """Computes lowercase hex SHA-256 checksum of a file on disk in 64KB chunks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    @staticmethod
    def compute_sha256_bytes(data: bytes) -> str:
        """Computes lowercase hex SHA-256 checksum of bytes."""
        return hashlib.sha256(data).hexdigest().lower()

    @classmethod
    def generate_checksums_content(cls, file_hashes: Dict[str, str]) -> bytes:
        """Generates GNU coreutils formatted checksums.sha256 content.

        Format: `<64-hex-sha256>  <normalized-relative-path>\n`
        Lexicographically sorted by relative path in ASCII order.
        Strictly UNIX LF (\\n).
        Excludes checksums.sha256 itself if present in file_hashes.
        """
        lines = []
        for path in sorted(file_hashes.keys()):
            if path in ("checksums.sha256", "checksums.txt"):
                continue
            sha = file_hashes[path].lower()
            lines.append(f"{sha}  {path}\n")

        return "".join(lines).encode("utf-8")

    @classmethod
    def parse_checksums_content(cls, content: str) -> Dict[str, str]:
        """Parses GNU coreutils formatted checksums file.

        Returns mapping: relative_path -> sha256_hash.
        """
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # GNU format has two spaces between hash and path
            parts = line.split("  ", 1)
            if len(parts) != 2:
                # Try single space fallback if malformed
                parts = line.split(" ", 1)
            if len(parts) == 2:
                sha = parts[0].strip().lower()
                rel_path = parts[1].strip()
                result[rel_path] = sha
        return result

    @classmethod
    def verify_sandbox_checksums(cls, sandbox_dir: str) -> Tuple[bool, Dict[str, Any]]:
        """Verifies sandbox directory against non-circular trust root.

        1. Reads and parses checksums.sha256.
        2. Verifies manifest.json against checksums.sha256 (TamperedManifestError).
        3. Verifies every payload file against checksums.sha256 (TamperedPayloadError).
        4. Cross-verifies manifest.json file_manifest against checksums.sha256 (ManifestChecksumDiscrepancyError).
        """
        checksums_path = os.path.join(sandbox_dir, "checksums.sha256")
        if not os.path.exists(checksums_path):
            raise ChecksumVerificationError("Cryptographic trust root 'checksums.sha256' missing from archive")

        with open(checksums_path, "r", encoding="utf-8") as f:
            checksums_raw = f.read()

        checksum_map = cls.parse_checksums_content(checksums_raw)

        # 1. manifest.json must be registered in checksums.sha256
        if "manifest.json" not in checksum_map:
            raise ChecksumVerificationError("'manifest.json' is not registered in checksums.sha256 trust root")

        manifest_path = os.path.join(sandbox_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise ChecksumVerificationError("'manifest.json' missing from extracted sandbox")

        actual_manifest_hash = cls.compute_sha256_file(manifest_path)
        expected_manifest_hash = checksum_map["manifest.json"]

        if actual_manifest_hash != expected_manifest_hash:
            raise TamperedManifestError(
                f"Manifest tampering detected! Computed hash '{actual_manifest_hash}' "
                f"does not match expected trust-root hash '{expected_manifest_hash}'"
            )

        # 2. Parse manifest.json
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        file_manifest = manifest_data.get("file_manifest", {})

        # 3. Verify all payload files in checksums.sha256
        for rel_path, expected_hash in checksum_map.items():
            if rel_path in ("manifest.json", "checksums.sha256"):
                continue

            target_file = os.path.join(sandbox_dir, rel_path)
            if not os.path.exists(target_file):
                raise TamperedPayloadError(f"Payload file '{rel_path}' registered in checksums is missing from archive")

            actual_hash = cls.compute_sha256_file(target_file)
            if actual_hash != expected_hash:
                raise TamperedPayloadError(
                    f"Payload tampering detected for '{rel_path}'! Computed '{actual_hash}' != expected '{expected_hash}'"
                )

        # 4. Cross-verify file_manifest from manifest.json
        for rel_path, entry in file_manifest.items():
            manifest_entry_hash = entry.get("sha256", "").lower()
            if rel_path not in checksum_map:
                raise ManifestChecksumDiscrepancyError(
                    f"File '{rel_path}' in manifest.json is not present in checksums.sha256"
                )
            if checksum_map[rel_path] != manifest_entry_hash:
                raise ManifestChecksumDiscrepancyError(
                    f"Hash mismatch between manifest.json ('{manifest_entry_hash}') "
                    f"and checksums.sha256 ('{checksum_map[rel_path]}') for '{rel_path}'"
                )

        # Ensure no unexpected files in checksums that aren't in manifest (except manifest.json)
        for rel_path in checksum_map:
            if rel_path == "manifest.json":
                continue
            if rel_path not in file_manifest:
                raise ManifestChecksumDiscrepancyError(
                    f"Payload file '{rel_path}' in checksums.sha256 is missing from manifest.json"
                )

        return True, manifest_data
