from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field


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


@dataclass
class SeedRegistry:
    base_seed: int = 42
    _coordinates_by_seed: dict[tuple[str, int], str] = field(
        default_factory=dict
    )

    def get(
        self,
        namespace: str,
        coordinates: Mapping[str, object],
    ) -> int:
        canonical = json.dumps(
            coordinates,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        seed = coordinate_seed(
            namespace,
            coordinates,
            base_seed=self.base_seed,
        )
        key = (namespace, seed)
        existing = self._coordinates_by_seed.get(key)
        if existing is not None and existing != canonical:
            raise ValueError(
                f"seed collision in namespace {namespace}: {seed}"
            )
        self._coordinates_by_seed[key] = canonical
        return seed
