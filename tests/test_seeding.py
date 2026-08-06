from pprs.seeding import SeedRegistry, coordinate_seed


def test_coordinate_seed_is_order_independent() -> None:
    first = coordinate_seed("call", {"task": "snli", "item": 1})
    second = coordinate_seed("call", {"item": 1, "task": "snli"})
    assert first == second


def test_namespaces_and_coordinates_change_seed() -> None:
    base = coordinate_seed("call", {"item": 1})
    assert base != coordinate_seed("option", {"item": 1})
    assert base != coordinate_seed("call", {"item": 2})


def test_seed_registry_reuses_same_coordinates() -> None:
    registry = SeedRegistry()
    first = registry.get("call", {"item": 1})
    second = registry.get("call", {"item": 1})
    assert first == second
