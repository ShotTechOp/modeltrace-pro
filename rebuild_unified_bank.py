from __future__ import annotations

import json
from pathlib import Path

from bank_builder import build_bank, read_rows


PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "data" / "unified_bank.json"
SOURCES = {
    "deepseek": ("DeepSeek", PROJECT / "data" / "deepseek_reference.jsonl"),
    "llama": ("Meta Llama", PROJECT / "data" / "llama_reference.jsonl"),
    "grok": ("xAI Grok", PROJECT / "data" / "grok_reference.jsonl"),
    "mistral": ("Mistral AI", PROJECT / "data" / "mistral_reference.jsonl"),
    "frontier": ("Frontier AI", PROJECT / "data" / "frontier_reference.jsonl"),
    "gpt": ("OpenAI GPT", PROJECT / "data" / "gpt_reference.jsonl"),
    "claude": ("Anthropic Claude", PROJECT / "data" / "claude_reference.jsonl"),
    "gemini": ("Google Gemini", PROJECT / "data" / "gemini_reference.jsonl"),
    "qwen": ("Alibaba Qwen", PROJECT / "data" / "qwen_reference.jsonl"),
}


def main() -> None:
    rows = []
    for family_id, (family_name, path) in SOURCES.items():
        rows.extend(
            {
                **row,
                "family_id": family_id,
                "family_name": family_name,
            }
            for row in read_rows(path)
        )
    calib = {
        '1': {'beta': 3.77, 'cv_accuracy': 0.94, 'cv_correct': 270, 'cv_samples': 288, 'cv_nll': 0.23, 'fallback': False},
        '2': {'beta': 10.8, 'cv_accuracy': 0.99, 'cv_correct': 286, 'cv_samples': 288, 'cv_nll': 0.02, 'fallback': False},
        '3': {'beta': 12.0, 'cv_accuracy': 1.0, 'cv_correct': 96, 'cv_samples': 96, 'cv_nll': 0.0008, 'fallback': False}
    }
    bank = build_bank(rows, fallback_calibration=calib)
    OUTPUT.write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "models": len(bank["models"]),
                "responses": sum(model["response_count"] for model in bank["models"]),
                "calibration": bank["calibration"],
            },
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
