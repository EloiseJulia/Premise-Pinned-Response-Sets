import json
from pathlib import Path

from pprs.reporting import render_all


def test_reporting_outputs_all_artifacts(tmp_path: Path) -> None:
    analysis = {
        "primary_temperature_0_7": {
            "beta_scatter_rows": [
                {
                    "task": "snli",
                    "beta_self": 0.2,
                    "beta_pin": 0.4,
                }
            ],
            "h1": {"r": 0.1},
            "diagnostic_rows": [
                {
                    "task": "snli",
                    "h_seed": 0.2,
                    "h_ctx": 0.5,
                }
            ],
            "high_risk_items": [
                {
                    "task": "snli",
                    "item_id": "i",
                    "model_snapshot": "m",
                    "temperature": 0.7,
                    "h_seed": 0.2,
                    "h_ctx": 0.5,
                    "dangerous": True,
                    "valid_forced_samples": 20,
                    "valid_pinned_values": 4,
                }
            ],
            "regret_surfaces": [
                {
                    "task": "snli",
                    "pi": 0.05,
                    "polarity": "not_applicable",
                    "tau": 0.5,
                    "metric": "MSE_pin",
                    "selected_model": "m",
                    "valid_models": 1,
                    "consistency_regret": 0.0,
                    "bias_regret": 0.0,
                }
            ],
        }
    }
    source = tmp_path / "analysis.json"
    source.write_text(json.dumps(analysis))
    outputs = render_all(source, tmp_path / "figures")
    assert all(path.exists() for path in outputs.values())
