"""Pure Python RFC 8032 Ed25519 signature verifier with strict curve and subgroup validation.

Production facility: VERIFICATION ONLY.
Zero signing or private-key operations are hosted in this production module.
Adversarial protections:
- Canonical coordinate decoding (y < 2^255 - 19, strict sign bit check)
- Strict scalar check (0 < S < L)
- Small subgroup and identity rejection (orders 1, 2, 4, 8 are rejected)
- Full cofactor equation check: [8][S]B == [8](R + [h]A)
"""
from __future__ import annotations

import hashlib
from typing import Optional, Tuple

# Field and Curve constants (RFC 8032)
_p: int = 2**255 - 19
_q: int = 2**252 + 27742317777372353535851937790883648493


def _modp_inv(x: int) -> int:
    return pow(x, _p - 2, _p)


_d: int = -121665 * _modp_inv(121666) % _p
_I: int = pow(2, (_p - 1) // 4, _p)


def _sha512_modq(s: bytes) -> int:
    return int.from_bytes(hashlib.sha512(s).digest(), "little") % _q


def _recover_x(y: int, sign: int) -> Optional[int]:
    if y >= _p:
        return None
    x2 = (y * y - 1) * _modp_inv(_d * y * y + 1) % _p
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p != 0:
        x = x * _I % _p
    if (x * x - x2) % _p != 0:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


_g_y: int = 4 * _modp_inv(5) % _p
_g_x: Optional[int] = _recover_x(_g_y, 0)
assert _g_x is not None
_G: Tuple[int, int, int, int] = (_g_x, _g_y, 1, _g_x * _g_y % _p)


def _point_add(P: Tuple[int, int, int, int], Q: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E = (B - A) % _p
    F = (D - C) % _p
    G = (D + C) % _p
    H = (B + A) % _p
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _point_mul(s: int, P: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    Q = (0, 1, 1, 0)  # Neutral element (0, 1)
    while s > 0:
        if s & 1:
            Q = _point_add(Q, P)
        P = _point_add(P, P)
        s >>= 1
    return Q


def _point_equal(P: Tuple[int, int, int, int], Q: Tuple[int, int, int, int]) -> bool:
    return (P[0] * Q[2] - Q[0] * P[2]) % _p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


def _point_decompress(s: bytes) -> Optional[Tuple[int, int, int, int]]:
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _p)


def ed25519_verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verify an RFC 8032 Ed25519 signature with strict subgroup validation.

    Accepts:
    - message: arbitrary bytes
    - signature: 64 bytes (R || S)
    - public_key: 32 bytes (A)

    Returns:
    - True if signature is valid and public key is non-degenerate.
    - False if any check fails or exception is raised.
    """
    if len(public_key) != 32 or len(signature) != 64:
        return False
    try:
        A = _point_decompress(public_key)
        if not A:
            return False
        Rs = signature[:32]
        R = _point_decompress(Rs)
        if not R:
            return False
        s = int.from_bytes(signature[32:], "little")
        if s <= 0 or s >= _q:
            return False

        neutral = (0, 1, 1, 0)
        # Reject identity points
        if _point_equal(A, neutral) or _point_equal(R, neutral):
            return False
        # Reject small-order points (order dividing 8)
        if _point_equal(_point_mul(8, A), neutral) or _point_equal(_point_mul(8, R), neutral):
            return False

        h = _sha512_modq(Rs + public_key + message)
        sB = _point_mul(s, _G)
        hA = _point_mul(h, A)
        R_plus_hA = _point_add(R, hA)
        # Check [8][s]B == [8](R + [h]A)
        return _point_equal(_point_mul(8, sB), _point_mul(8, R_plus_hA))
    except Exception:
        return False
