#!/usr/bin/env python3
"""
ModelTrace Pro - CodeCraft API Forensic Probe & Auditor
Tests models provided by CodeCraft API (https://codecraftapi.com/v1)
and matches them against the 66 calibrated model centroids in ModelTrace.
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from fingerprint import analyze_global_outputs, generate_challenges, load_bank

BASE_URL = "https://codecraftapi.com/v1"

def fetch_models(api_key: str):
    url = f"{BASE_URL}/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ModelTrace-Forensics/2.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
        return []
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def query_chat(api_key: str, model_id: str, prompt: str) -> str:
    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 1200
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ModelTrace-Forensics/2.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"[{model_id}] HTTP {e.code}: {err_body}")
        return ""
    except Exception as e:
        print(f"[{model_id}] Request error: {e}")
        return ""

def audit_model(api_key: str, model_id: str, bank: dict):
    print(f"\n=======================================================")
    print(f"AUDITING: {model_id}")
    print(f"=======================================================")
    challenges = generate_challenges(count=3)
    outputs = []
    
    for i, ch in enumerate(challenges, 1):
        print(f"[*] Sending Probe {i}/3 ({ch['expected_count']} integers required)...")
        reply = query_chat(api_key, model_id, ch["prompt"])
        if not reply:
            print(f"[-] Empty or failed response from {model_id}")
            continue
        print(f"    Received {len(reply)} chars. Sample: {reply[:70].strip()}...")
        outputs.append({
            "expected_count": ch["expected_count"],
            "text": reply
        })

    if not outputs:
        print(f"[!] Could not collect probe responses for {model_id}")
        return

    try:
        report = analyze_global_outputs(outputs, bank)
        best = report["results"][0]
        runner_up = report["results"][1] if len(report["results"]) > 1 else None
        
        print("\n--- FORENSIC ATTRIBUTION REPORT ---")
        print(f"Target Model Tested:     {model_id}")
        print(f"Predicted Family:        {report.get('family_prediction_name', 'Unknown')} ({report.get('family_probability', 0)*100:.1f}%)")
        print(f"Top 1 Model Match:       {best['model']} ({best['probability']*100:.1f}%)")
        print(f"Top 1 Similarity:        {best['similarity']:.3f}")
        if runner_up:
            print(f"Top 2 Runner-up:         {runner_up['model']} ({runner_up['probability']*100:.1f}%)")
        print(f"Confidence Level:        {report.get('confidence_level', 'N/A')}")
        print(f"OOD / Anomaly Score:     {report.get('ood_score', 'Normal')}")
        
        # Verdict logic
        if "claude" in best["model"] and best["similarity"] > 0.65:
            print(f"[VERDICT] GENUINE ANTHROPIC CLAUDE WEIGHTS CONFIRMED (Matched {best['model']})")
        elif best["similarity"] < 0.50:
            print(f"[VERDICT] OOD / SYNTHETIC SCRIPT PROXY DETECTED (Similarity {best['similarity']:.3f} below threshold)")
        else:
            print(f"[VERDICT] REROUTED / MISMATCHED MODEL (Advertised: {model_id}, Actual: {best['model']})")
    except Exception as e:
        print(f"[!] Analysis error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python audit_codecraft.py <CODECRAFT_API_KEY>")
        sys.exit(1)
        
    api_key = sys.argv[1].strip()
    print(f"Connecting to CodeCraft API ({BASE_URL})...")
    models = fetch_models(api_key)
    
    if not models:
        print("No models returned or invalid API key.")
        sys.exit(1)
        
    model_ids = [m["id"] for m in models]
    print(f"\n[+] Successfully retrieved {len(model_ids)} models from CodeCraft:")
    for mid in sorted(model_ids):
        print(f"  - {mid}")
        
    bank = load_bank(PROJECT_DIR / "data" / "unified_bank.json")
    
    # Priority targets requested by user
    targets = [
        "claude-opus-5-5",
        "claude-opus-5",
        "claude-fable-5.1",
        "claude-fable-5",
        "claude-opus-4.8"
    ]
    
    # Find matching models available on the provider
    to_test = []
    for t in targets:
        for mid in model_ids:
            if t in mid or mid in t:
                if mid not in to_test:
                    to_test.append(mid)
                    
    # Also test any model containing 'fable' or 'opus'
    for mid in model_ids:
        if ("fable" in mid.lower() or "opus" in mid.lower()) and mid not in to_test:
            to_test.append(mid)
            
    print(f"\nSelected {len(to_test)} target models for forensic audit: {to_test}")
    for mid in to_test:
        audit_model(api_key, mid, bank)

if __name__ == "__main__":
    main()
