from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


def coordinate_seed(
    namespace: str,
    coordinates: Mapping[str, object],
    *,
    base_seed: int = 42,
) -> int:
    if not namespace.strip():
        raise ValueError("seed namespace cannot be blank")
    canonical = json.dumps(
        {
            "namespace": namespace,
            "base_seed": base_seed,
            "coordinates": coordinates,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31)
