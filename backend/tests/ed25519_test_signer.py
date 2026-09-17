"""Test-only helper for Ed25519 signing and test key derivation.
STRICTLY FOR TESTS: Not imported or used by production code.
"""
from __future__ import annotations

import hashlib
from typing import Tuple

from app.services.ed25519_pure import _p, _q, _G, _modp_inv, _point_add, _point_mul, _point_decompress, _sha512_modq


def point_compress(P: Tuple[int, int, int, int]) -> bytes:
    zinv = _modp_inv(P[2])
    x = P[0] * zinv % _p
    y = P[1] * zinv % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def secret_expand(secret: bytes) -> Tuple[int, bytes]:
    if len(secret) != 32:
        raise ValueError("Bad size of private key")
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key_from_seed(secret: bytes) -> bytes:
    a, _ = secret_expand(secret)
    return point_compress(_point_mul(a, _G))


def ed25519_sign(message: bytes, secret: bytes) -> bytes:
    a, prefix = secret_expand(secret)
    A = point_compress(_point_mul(a, _G))
    r = _sha512_modq(prefix + message)
    R = _point_mul(r, _G)
    Rs = point_compress(R)
    h = _sha512_modq(Rs + A + message)
    s = (r + h * a) % _q
    return Rs + int.to_bytes(s, 32, "little")
