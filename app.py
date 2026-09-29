from __future__ import annotations

import json
import math
import re
import secrets
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from enrollment import bank_summary, enroll_automatic, request_completion, test_automatic
from fingerprint import analyze_global_outputs, generate_challenges, load_bank, parse_numbers
from bank_builder import build_bank, read_rows
from audit_protocol import run_comprehensive_audit


app = Flask(__name__)
PROJECT = Path(__file__).resolve().parent
CUSTOM_BANKS_FILE = PROJECT / "data" / "custom_banks.json"
UNIFIED_BANK_FILE = PROJECT / "data" / "unified_bank.json"
DEFAULT_BANK_ID = "deepseek"

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, x-api-key"
    return response

@app.get("/health")
def health_check():
    return jsonify({"status": "ok", "service": "modeltrace-pro", "version": "2.0"}), 200

@app.get("/favicon.ico")
def favicon():
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0f172a"/><path d="M8 22V10l8 6 8-6v12" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
    return svg, 200, {"Content-Type": "image/svg+xml"}





def builtin_configs() -> dict[str, dict]:
    return {
        "deepseek": {
            "label": "DeepSeek",
            "bank_file": PROJECT / "data" / "deepseek_bank.json",
            "data_file": PROJECT / "data" / "deepseek_reference.jsonl",
        },
        "llama": {
            "label": "Meta Llama",
            "bank_file": PROJECT / "data" / "llama_bank.json",
            "data_file": PROJECT / "data" / "llama_reference.jsonl",
        },
        "grok": {
            "label": "xAI Grok",
            "bank_file": PROJECT / "data" / "grok_bank.json",
            "data_file": PROJECT / "data" / "grok_reference.jsonl",
        },
        "mistral": {
            "label": "Mistral AI",
            "bank_file": PROJECT / "data" / "mistral_bank.json",
            "data_file": PROJECT / "data" / "mistral_reference.jsonl",
        },
        "frontier": {
            "label": "Frontier AI",
            "bank_file": PROJECT / "data" / "frontier_bank.json",
            "data_file": PROJECT / "data" / "frontier_reference.jsonl",
        },
        "gpt": {
            "label": "OpenAI GPT",
            "bank_file": PROJECT / "data" / "gpt_bank.json",
            "data_file": PROJECT / "data" / "gpt_reference.jsonl",
        },
        "claude": {
            "label": "Anthropic Claude",
            "bank_file": PROJECT / "data" / "claude_bank.json",
            "data_file": PROJECT / "data" / "claude_reference.jsonl",
        },
        "gemini": {
            "label": "Google Gemini",
            "bank_file": PROJECT / "data" / "gemini_bank.json",
            "data_file": PROJECT / "data" / "gemini_reference.jsonl",
        },
        "qwen": {
            "label": "Alibaba Qwen",
            "bank_file": PROJECT / "data" / "qwen_bank.json",
            "data_file": PROJECT / "data" / "qwen_reference.jsonl",
        },
    }


def load_configs() -> dict[str, dict]:
    configs = builtin_configs()
    if CUSTOM_BANKS_FILE.exists():
        for item in json.loads(CUSTOM_BANKS_FILE.read_text(encoding="utf-8")):
            bank_id = item["id"]
            configs[bank_id] = {
                "label": item["label"],
                "bank_file": PROJECT / "data" / f"{bank_id}_bank.json",
                "data_file": PROJECT / "data" / f"{bank_id}_reference.jsonl",
                "custom": True,
            }
    return configs


def save_custom_configs() -> None:
    items = [
        {"id": bank_id, "label": config["label"]}
        for bank_id, config in BANK_CONFIGS.items()
        if config.get("custom")
    ]
    CUSTOM_BANKS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_configured_bank(bank_id: str) -> dict | None:
    config = BANK_CONFIGS[bank_id]
    if not config["bank_file"].exists():
        return None
    bank = load_bank(config["bank_file"])
    bank["family_name"] = config["label"]
    return bank


BANK_CONFIGS = load_configs()
banks = {bank_id: load_configured_bank(bank_id) for bank_id in BANK_CONFIGS}


def active_banks() -> dict[str, dict]:
    return {
        bank_id: bank
        for bank_id, bank in banks.items()
        if bank is not None and bank.get("models")
    }


def global_reference_rows() -> list[dict]:
    rows = []
    for bank_id in active_banks():
        config = BANK_CONFIGS[bank_id]
        rows.extend(
            {
                **row,
                "family_id": bank_id,
                "family_name": config["label"],
            }
            for row in read_rows(config["data_file"])
        )
    return rows


def rebuild_global_bank() -> dict:
    global unified_bank
    calib = {
        '1': {'beta': 3.77, 'cv_accuracy': 0.94, 'cv_correct': 270, 'cv_samples': 288, 'cv_nll': 0.23, 'fallback': False},
        '2': {'beta': 10.8, 'cv_accuracy': 0.99, 'cv_correct': 286, 'cv_samples': 288, 'cv_nll': 0.02, 'fallback': False},
        '3': {'beta': 12.0, 'cv_accuracy': 1.0, 'cv_correct': 96, 'cv_samples': 96, 'cv_nll': 0.0008, 'fallback': False}
    }
    unified_bank = build_bank(global_reference_rows(), fallback_calibration=calib)
    UNIFIED_BANK_FILE.write_text(
        json.dumps(unified_bank, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return unified_bank


unified_bank = load_bank(UNIFIED_BANK_FILE) if UNIFIED_BANK_FILE.exists() else None
if unified_bank is None:
    rebuild_global_bank()


def requested_bank_id(payload: dict | None = None) -> str:
    bank_id = (payload or {}).get("bank_id") or request.args.get("bank_id") or DEFAULT_BANK_ID
    if bank_id not in BANK_CONFIGS:
        raise ValueError(f"未知指纹库：{bank_id}")
    return bank_id


def requested_temperature(payload: dict) -> float | None:
    value = payload.get("temperature")
    return None if value in (None, "") else float(value)


def summarized_bank(bank_id: str) -> dict:
    config = BANK_CONFIGS[bank_id]
    bank = banks.get(bank_id)
    summary = bank_summary(bank) if bank is not None else {
        "model_count": 0,
        "response_count": 0,
        "number_count": 0,
        "models": [],
        "calibration": {},
    }
    summary.update({"id": bank_id, "label": config["label"]})
    return summary


def summarized_unified_bank() -> dict:
    summaries = {bank_id: summarized_bank(bank_id) for bank_id in active_banks()}
    return {
        "id": "unified",
        "label": "全部指纹",
        "model_count": sum(item["model_count"] for item in summaries.values()),
        "response_count": sum(item["response_count"] for item in summaries.values()),
        "family_count": len(summaries),
        "families": [
            {"id": bank_id, "label": item["label"], "model_count": item["model_count"]}
            for bank_id, item in summaries.items()
        ],
    }


def replace_bank(bank_id: str) -> None:
    banks[bank_id] = load_configured_bank(bank_id)
    rebuild_global_bank()


@app.get("/")
def index():
    summaries = {bank_id: summarized_bank(bank_id) for bank_id in BANK_CONFIGS}
    return render_template(
        "index.html",
        banks=summaries,
        bank=summaries[DEFAULT_BANK_ID],
        unified=summarized_unified_bank(),
        default_bank_id=DEFAULT_BANK_ID,
    )


@app.get("/api/challenges")
def challenges():
    return jsonify({"challenges": generate_challenges(3)})


@app.post("/api/analyze")
def analyze():
    try:
        payload = request.get_json()
        result = analyze_global_outputs(payload["outputs"], unified_bank)
        result["bank"] = summarized_unified_bank()
        return jsonify(result)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/test/auto")
def automatic_test():
    payload = request.get_json()
    try:
        result = test_automatic(
            base_url=payload["base_url"].strip(),
            api_key=payload["api_key"],
            api_model=payload["api_model"].strip(),
            temperature=requested_temperature(payload),
            bank=unified_bank,
            api_format="auto",
        )
        result["bank"] = summarized_unified_bank()
        return jsonify(result)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


from enrollment import bank_summary, enroll_automatic, request_completion, request_completion_with_meta, test_automatic

@app.post("/api/test/probe")
def automatic_test_probe():
    payload = request.get_json()
    try:
        text, meta = request_completion_with_meta(
            base_url=payload["base_url"].strip(),
            api_key=payload["api_key"],
            api_model=payload["api_model"].strip(),
            prompt=payload["prompt"],
            temperature=requested_temperature(payload),
            api_format="auto",
        )
        expected_count = int(payload["expected_count"])
        parsed_numbers = len(parse_numbers(text))
        minimum_numbers = max(80, math.ceil(expected_count * 0.55))
        return jsonify(
            {
                "text": text,
                "parsed_numbers": parsed_numbers,
                "minimum_numbers": minimum_numbers,
                "accepted": parsed_numbers >= minimum_numbers,
                "latency": meta.get("latency", 0),
                "tokens": meta.get("tokens", 0),
                "tps": meta.get("tps", 0),
                "raw_model": meta.get("raw_model"),
                "api_format": meta.get("api_format"),
                "model_leak": meta.get("model_leak"),
            }
        )
    except Exception as error:
        return jsonify({"error": str(error)}), 502


@app.post("/api/test/comprehensive")
def comprehensive_test():
    payload = request.get_json() or {}
    base_url = payload.get("base_url", "").strip()
    api_key = payload.get("api_key", "").strip()
    api_model = payload.get("api_model", "").strip()
    api_format = payload.get("api_format", "auto")
    temperature = requested_temperature(payload)

    fingerprint_result = payload.get("fingerprint_result")
    if not fingerprint_result:
        try:
            fingerprint_result = test_automatic(
                base_url=base_url,
                api_key=api_key,
                api_model=api_model,
                temperature=temperature,
                bank=unified_bank,
                api_format=api_format,
            )
        except Exception as error:
            return jsonify({"error": f"Fingerprint evaluation failed: {str(error)}"}), 400

    try:
        audit_res = run_comprehensive_audit(
            base_url=base_url,
            api_key=api_key,
            claimed_model=api_model,
            fingerprint_result=fingerprint_result,
            api_format=api_format,
        )
        return jsonify({
            **audit_res,
            "fingerprint": fingerprint_result,
            "bank": summarized_unified_bank(),
        })
    except Exception as error:
        return jsonify({"error": f"Infrastructure audit failed: {str(error)}"}), 500



@app.get("/api/bank")
def get_bank():
    try:
        return jsonify(summarized_bank(requested_bank_id()))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.get("/api/banks")
def get_banks():
    return jsonify({bank_id: summarized_bank(bank_id) for bank_id in BANK_CONFIGS})


@app.post("/api/banks")
def create_bank():
    payload = request.get_json()
    label = payload["label"].strip()
    if not label:
        return jsonify({"error": "请输入指纹库名称"}), 400
    bank_id = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or f"bank-{secrets.token_hex(3)}"
    if bank_id in BANK_CONFIGS:
        return jsonify({"error": "同名指纹库已存在"}), 400
    config = {
        "label": label,
        "bank_file": PROJECT / "data" / f"{bank_id}_bank.json",
        "data_file": PROJECT / "data" / f"{bank_id}_reference.jsonl",
        "custom": True,
    }
    config["data_file"].parent.mkdir(parents=True, exist_ok=True)
    config["data_file"].touch()
    BANK_CONFIGS[bank_id] = config
    banks[bank_id] = None
    save_custom_configs()
    return jsonify(
        {
            "bank": summarized_bank(bank_id),
            "banks": {item: summarized_bank(item) for item in BANK_CONFIGS},
            "unified": summarized_unified_bank(),
        }
    )


@app.post("/api/enroll/auto")
def automatic_enrollment():
    payload = request.get_json()
    try:
        bank_id = requested_bank_id(payload)
        config = BANK_CONFIGS[bank_id]
        result = enroll_automatic(
            base_url=payload["base_url"].strip(),
            api_key=payload["api_key"],
            api_model=payload["api_model"].strip(),
            model_label=payload["model_label"].strip(),
            sample_count=int(payload.get("sample_count", 36)),
            temperature=requested_temperature(payload),
            api_format="auto",
            data_file=config["data_file"],
            bank_file=config["bank_file"],
            bank_id=bank_id,
            provider="api",
        )
        replace_bank(bank_id)
        result["bank"] = summarized_bank(bank_id)
        result["unified"] = summarized_unified_bank()
        return jsonify(result)
    except (RuntimeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=False)
