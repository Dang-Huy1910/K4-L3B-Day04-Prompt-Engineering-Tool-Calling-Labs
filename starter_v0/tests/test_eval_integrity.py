from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

EXPECTED_HASHES = {
    "eval_base.json": "8d9b4180a2d3715fd1351efb4990af20e0b149d40e6155510f2605fecb2ec3ed",
    "eval_adversarial.json": "f433fd8697075d9c5534a4a60a58c32c3d9c7b6f6080a7fc63aa59dcc3bec718",
    "eval_helpdesk_extension.json": "e8b5960ea12b93bdfa08d27ef1c81471548c4e3c9ca48c4786b65e6cb1a5121e",
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fixed_eval_datasets_integrity():
    for filename, expected_hash in EXPECTED_HASHES.items():
        path = DATA_DIR / filename
        assert path.exists(), f"Missing required eval dataset: {path}"
        actual_hash = file_sha256(path)
        assert actual_hash == expected_hash, (
            f"Integrity violation in {filename}!\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}\n"
            "Modifying fixed eval datasets to increase scores is strictly forbidden."
        )

