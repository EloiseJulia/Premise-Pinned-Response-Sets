def test_smoke_review_uses_twenty_evenly_spaced_indices() -> None:
    total = 100
    indices = [
        round(index * (total - 1) / 19) for index in range(20)
    ]
    assert len(indices) == 20
    assert len(set(indices)) == 20
    assert indices[0] == 0
    assert indices[-1] == 99
