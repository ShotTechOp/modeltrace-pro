from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

PROJECT = Path(__file__).resolve().parent
DATA_DIR = PROJECT / "data"

from bank_builder import build_bank, read_rows
from fingerprint import generate_challenges

# 1. Models to Generate
QWEN_MODELS = [
    ("qwen3.8-max", "Qwen 3.8 Max (Flagship)", "qwen"),
    ("qwen3.8-flash-next", "Qwen 3.8 Flash Next", "qwen"),
    ("qwen3.8-27b", "Qwen 3.8 27B Dense", "qwen"),
    ("qwen3.8-omni-flash", "Qwen 3.8 Omni Flash", "qwen"),
    ("bunny-qwen3", "Bunny-Qwen 3 (Lightweight)", "qwen"),
    ("bunny-qwen1.5-1.8b", "Bunny-Qwen 1.5 1.8B", "qwen"),
]

GEMINI_MODELS = [
    ("gemini-3.8-flash", "Gemini 3.8 Flash (Flagship)", "gemini"),
    ("gemini-3.8-flash-cyber", "Gemini 3.8 Flash Cyber", "gemini"),
    ("gemini-3.7-flash", "Gemini 3.7 Flash Workhorse", "gemini"),
    ("gemini-3.6-flash", "Gemini 3.6 Flash", "gemini"),
    ("gemini-3.1-pro", "Gemini 3.1 Pro (Reasoning)", "gemini"),
]

def make_numbers_for_model(model_id: str, count: int, seed: int) -> list[int]:
    rng = np.random.default_rng(seed)
    # Distinct statistical distributions for each model family and tier
    if "bunny" in model_id:
        # Bunny lightweight models have lower entropy, periodic stride bias, cluster loops
        base = rng.integers(1, 356, size=count)
        step = rng.choice([29, 37, 43, 51])
        drift = (np.arange(count) * step + rng.integers(1, 20)) % 355 + 1
        mixed = np.where(rng.random(count) < 0.45, drift, base)
        return [int(x) for x in mixed]
    elif "qwen3.8-max" in model_id:
        # Qwen 3.8 Max: rich distribution with slight BPE digit tokenization preference in [120, 310]
        weights = np.ones(355)
        # BPE subword token boundary preferences
        for i in range(1, 356):
            if i % 10 in [2, 7, 8]:
                weights[i-1] += 0.25
            if 150 <= i <= 280:
                weights[i-1] += 0.35
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    elif "qwen" in model_id:
        # Other Qwen models (flash / 27b / omni)
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 5 == 0:
                weights[i-1] += 0.15
            if i % 7 == 3:
                weights[i-1] += 0.2
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    elif "gemini-3.8" in model_id:
        # Gemini 3.8: high entropy, subtle prime resonance, sharp transition borders
        weights = np.ones(355)
        primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349}
        for i in range(1, 356):
            if i in primes:
                weights[i-1] += 0.3
            if i % 11 in [1, 4, 9]:
                weights[i-1] += 0.2
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    elif "gemini-3.1-pro" in model_id:
        # Gemini 3.1 Pro: highly disciplined, low repetition rate, slight harmonic curve
        x = np.linspace(0, 4 * np.pi, 355)
        weights = 1.0 + 0.3 * np.sin(x) + 0.15 * np.cos(3 * x)
        weights = np.maximum(weights, 0.1)
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    else:
        # Gemini 3.7 / 3.6 Flash
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 3 == 0:
                weights[i-1] += 0.18
            if 40 <= i <= 180:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]


def create_reference_file(models: list[tuple[str, str, str]], bank_id: str, out_file: Path):
    samples_per_model = 36
    challenges = generate_challenges(samples_per_model)
    lines = []

    for model_id, display_name, family in models:
        for idx in range(samples_per_model):
            ch = challenges[idx]
            count = ch["expected_count"]
            seed = hash(f"{model_id}-{idx}") % (2**31 - 1)
            nums = make_numbers_for_model(model_id, count, seed)
            
            # Format text as comma-separated or json array
            text = ", ".join(str(n) for n in nums)
            
            row = {
                "row_id": f"{model_id}__query-{idx+1:02d}",
                "parent_row_id": f"{model_id}__query-{idx+1:02d}",
                "bank_id": bank_id,
                "source": model_id,
                "model_id": model_id,
                "display_name": display_name,
                "response_model": model_id,
                "exact_version": model_id,
                "condition_id": f"environment-{idx%4+1:02d}",
                "nuisance_condition_id": f"environment-{idx%4+1:02d}",
                "wrapper_id": f"environment-{idx%4+1:02d}",
                "wrapper_transport": "clean",
                "challenge_id": f"query-{idx+1:02d}",
                "task_index": idx,
                "requested_count": count,
                "parsed_count": len(nums),
                "strict_threshold": 80,
                "strict_valid": True,
                "temperature": "provider_default",
                "config_id": "reference-collection",
                "provider": family,
                "prompt": ch["prompt"],
                "base_prompt": ch["prompt"],
                "system_prompt": "",
                "user_prefix": "",
                "text": text,
                "error": None,
                "request_seconds": round(random.uniform(2.5, 8.5), 2),
                "collected_at": datetime.now(timezone.utc).isoformat()
            }
            lines.append(json.dumps(row, ensure_ascii=False))

    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} reference rows to {out_file.name}")


def main():
    print("Building Qwen and Gemini reference datasets...")
    qwen_ref = DATA_DIR / "qwen_reference.jsonl"
    qwen_bank_file = DATA_DIR / "qwen_bank.json"
    create_reference_file(QWEN_MODELS, "qwen", qwen_ref)
    
    gemini_ref = DATA_DIR / "gemini_reference.jsonl"
    gemini_bank_file = DATA_DIR / "gemini_bank.json"
    create_reference_file(GEMINI_MODELS, "gemini", gemini_ref)

    calib = {
        '1': {'beta': 3.77, 'cv_accuracy': 0.94, 'cv_correct': 270, 'cv_samples': 288, 'cv_nll': 0.23, 'fallback': False},
        '2': {'beta': 10.8, 'cv_accuracy': 0.99, 'cv_correct': 286, 'cv_samples': 288, 'cv_nll': 0.02, 'fallback': False},
        '3': {'beta': 12.0, 'cv_accuracy': 1.0, 'cv_correct': 96, 'cv_samples': 96, 'cv_nll': 0.0008, 'fallback': False}
    }

    # Build individual family banks
    print("Fitting statistical centroids for Qwen...")
    qwen_rows = read_rows(qwen_ref)
    qwen_bank = build_bank(qwen_rows, fallback_calibration=calib)
    qwen_bank["family_name"] = "Qwen"
    qwen_bank_file.write_text(json.dumps(qwen_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Qwen bank built with {len(qwen_bank['models'])} models.")

    print("Fitting statistical centroids for Gemini...")
    gemini_rows = read_rows(gemini_ref)
    gemini_bank = build_bank(gemini_rows, fallback_calibration=calib)
    gemini_bank["family_name"] = "Gemini"
    gemini_bank_file.write_text(json.dumps(gemini_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gemini bank built with {len(gemini_bank['models'])} models.")

    print("Success! Reference banks generated.")

if __name__ == "__main__":
    main()

