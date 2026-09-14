"""Pure Python Ed25519 (RFC 8032) signing and verification.
Zero external dependencies, standard library hashlib only.
"""
from __future__ import annotations

import hashlib
from typing import Tuple

# Curve parameters
_b = 256
_q = 2**255 - 19
_l = 2**252 + 27742317777372353535851937790883648493


def _inv(z: int) -> int:
    return pow(z, _q - 2, _q)


_d = -121665 * _inv(121666) % _q
_I = pow(2, (_q - 1) // 4, _q)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (_q + 3) // 8, _q)
    if (x * x - xx) % _q != 0:
        x = (x * _I) % _q
    if x % 2 != 0:
        x = _q - x
    return x


_By = 4 * _inv(5) % _q
_Bx = _xrecover(_By)
_B = (_Bx % _q, _By % _q, 1, (_Bx * _By) % _q)


def _edwards_add(P: Tuple[int, int, int, int], Q: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    # Extended coordinates addition
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    A = (y1 - x1) * (y2 - x2) % _q
    B = (y1 + x1) * (y2 + x2) % _q
    C = t1 * 2 * _d * t2 % _q
    D = z1 * 2 * z2 % _q
    E = (B - A) % _q
    F = (D - C) % _q
    G = (D + C) % _q
    H = (B + A) % _q
    return (E * F % _q, G * H % _q, F * G % _q, E * H % _q)


def _scalarmult(P: Tuple[int, int, int, int], e: int) -> Tuple[int, int, int, int]:
    if e == 0:
        return (0, 1, 1, 0)
    Q = _scalarmult(P, e // 2)
    Q = _edwards_add(Q, Q)
    if e & 1:
        Q = _edwards_add(Q, P)
    return Q


def _encode_point(P: Tuple[int, int, int, int]) -> bytes:
    x, y, z, _ = P
    inv_z = _inv(z)
    x_aff = x * inv_z % _q
    y_aff = y * inv_z % _q
    s = bytearray(y_aff.to_bytes(32, "little"))
    if x_aff & 1:
        s[31] |= 0x80
    return bytes(s)


def _decode_point(s: bytes) -> Tuple[int, int, int, int]:
    if len(s) != 32:
        raise ValueError("Invalid point length")
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if bool(x & 1) != bool(s[31] & 0x80):
        x = _q - x
    return (x, y, 1, x * y % _q)


def public_key_from_seed(seed_32: bytes) -> bytes:
    """Derive 32-byte Ed25519 public key from 32-byte private seed."""
    h = hashlib.sha512(seed_32).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    A = _scalarmult(_B, a)
    return _encode_point(A)


def ed25519_sign(message: bytes, seed_32: bytes) -> bytes:
    """Sign message with 32-byte private seed; returns 64-byte signature."""
    h = hashlib.sha512(seed_32).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    A_bytes = _encode_point(_scalarmult(_B, a))
    prefix = h[32:]
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % _l
    R = _scalarmult(_B, r)
    R_bytes = _encode_point(R)
    k = int.from_bytes(hashlib.sha512(R_bytes + A_bytes + message).digest(), "little") % _l
    S = (r + k * a) % _l
    return R_bytes + S.to_bytes(32, "little")


def ed25519_verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verify 64-byte signature against 32-byte public key and message."""
    if len(signature) != 64 or len(public_key) != 32:
        return False
    try:
        R_bytes = signature[:32]
        S_bytes = signature[32:]
        S = int.from_bytes(S_bytes, "little")
        if S >= _l:
            return False
        A = _decode_point(public_key)
        k = int.from_bytes(hashlib.sha512(R_bytes + public_key + message).digest(), "little") % _l
        SB = _scalarmult(_B, S)
        R = _decode_point(R_bytes)
        kA = _scalarmult(A, k)
        R_plus_kA = _edwards_add(R, kA)
        # Check affine equality
        return (SB[0] * R_plus_kA[2] - R_plus_kA[0] * SB[2]) % _q == 0 and \
               (SB[1] * R_plus_kA[2] - R_plus_kA[1] * SB[2]) % _q == 0
    except Exception:
        return False
