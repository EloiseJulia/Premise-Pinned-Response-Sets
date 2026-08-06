import json
from pathlib import Path


def test_preregistered_subset_sizes() -> None:
    smoke = json.loads(
        Path("configs/samples/smoke-v1.json").read_text()
    )
    full_grid = json.loads(
        Path("configs/samples/full-grid-ablation-v1.json").read_text()
    )
    assert sum(len(items) for items in smoke["items"].values()) == 10
    assert {
        task: len(items) for task, items in full_grid["items"].items()
    } == {
        "chaosnli_snli": 20,
        "chaosnli_mnli": 20,
        "summeval_relevance": 20,
    }
