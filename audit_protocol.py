from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA"
    "AET3RJTUUH6AEVDwA1n73rPAAAAAZJREFUCNdj+A8AAQEB/vX5p6UAAAAASUVORK5CYII="
)

USER_AGENT = (
    "ModelTrace-Pro/2.5 (Windows 10.0.26200; x86_64) ForensicAuditEngine/2.5"
)


def _http_request(url: str, body: dict, headers: dict, timeout: int = 15) -> tuple[int, dict, dict[str, str], float]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = round(time.time() - t0, 2)
            resp_headers = {k.lower(): v for k, v in resp.getheaders()}
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw.strip() else {}
            return resp.status, parsed, resp_headers, elapsed
    except urllib.error.HTTPError as err:
        elapsed = round(time.time() - t0, 2)
        resp_headers = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
        raw = err.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"error": raw}
        return err.code, parsed, resp_headers, elapsed
    except Exception as err:
        elapsed = round(time.time() - t0, 2)
        return 0, {"error": str(err)}, {}, elapsed


def audit_stream_structure(base_url: str, api_key: str, model: str, is_anthropic: bool) -> dict:
    url = base_url.rstrip("/") + ("/v1/messages" if is_anthropic else "/v1/chat/completions")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept": "text/event-stream",
    }
    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {
            "model": model,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Respond with 'ok'."}],
            "stream": True,
        }
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": model,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Respond with 'ok'."}],
            "stream": True,
        }

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    events_seen = []
    has_sse_format = False
    is_native = False

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "event-stream" in content_type:
                has_sse_format = True
            
            lines = []
            for _ in range(30):
                line = resp.readline().decode("utf-8", errors="replace")
                if not line:
                    break
                lines.append(line.strip())
                if line.startswith("event:"):
                    events_seen.append(line.split(":", 1)[1].strip())
            
            if is_anthropic:
                # Native Anthropic stream MUST emit message_start, content_block_delta, or message_delta
                expected = {"message_start", "content_block_start", "content_block_delta", "message_delta", "message_stop"}
                matched = set(events_seen).intersection(expected)
                if len(matched) >= 2:
                    is_native = True
                elif any("data:" in l for l in lines) and not events_seen:
                    # Generic OpenAI-style streaming sent to Anthropic endpoint -> Transcoded proxy
                    is_native = False
            else:
                # OpenAI style streaming
                if any(l.startswith("data:") and "choices" in l for l in lines):
                    is_native = True
                    has_sse_format = True

        status = "pass" if is_native else ("warn" if has_sse_format else "fail")
        note = "Native SSE Frames Verified" if is_native else ("Transcoded / Non-Native SSE Proxy" if has_sse_format else "SSE Stream Rejected")
        return {"id": "stream_structure", "label": "Stream Structure", "status": status, "note": note, "events": events_seen[:4]}
    except Exception as err:
        return {"id": "stream_structure", "label": "Stream Structure", "status": "fail", "note": f"Stream error: {str(err)[:50]}"}


def audit_signature_and_headers(resp_headers: dict[str, str], is_anthropic: bool) -> dict:
    leak_signatures = []
    # Check for reverse-proxy middleware headers
    for h, val in resp_headers.items():
        if h in ("x-oneapi-request-id", "oneapi-request-id"):
            leak_signatures.append("OneAPI Proxy Bridge")
        elif h in ("x-newapi-request-id", "newapi-request-id"):
            leak_signatures.append("NewAPI Gateway")
        elif h.startswith("cf-") and "worker" in val.lower():
            leak_signatures.append("Cloudflare Worker Intermediary")
        elif h == "x-relay-provider":
            leak_signatures.append(f"Relay Header ({val})")

    server = resp_headers.get("server", "").lower()
    if is_anthropic:
        has_ratelimit = any(k.startswith("anthropic-ratelimit-") for k in resp_headers)
        has_req_id = "request-id" in resp_headers
        if not has_ratelimit and not has_req_id:
            leak_signatures.append("Missing Official Anthropic RateLimit Headers")

    status = "fail" if leak_signatures else "pass"
    note = f"Proxy Signatures Detected: {', '.join(leak_signatures)}" if leak_signatures else "Clean Upstream Header Signature"
    return {"id": "signature_analysis", "label": "Signature Analysis", "status": status, "note": note, "signatures": leak_signatures}


def audit_tool_use(base_url: str, api_key: str, model: str, is_anthropic: bool) -> dict:
    url = base_url.rstrip("/") + ("/v1/messages" if is_anthropic else "/v1/chat/completions")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {
            "model": model,
            "max_tokens": 80,
            "tools": [{
                "name": "lookup_auth",
                "description": "Authenticate diagnostic hash",
                "input_schema": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"]
                }
            }],
            "messages": [{"role": "user", "content": "Call the lookup_auth tool with code 'MT_PROBE'."}],
        }
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": model,
            "max_tokens": 80,
            "tools": [{
                "type": "function",
                "function": {
                    "name": "lookup_auth",
                    "description": "Authenticate diagnostic hash",
                    "parameters": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"]
                    }
                }
            }],
            "messages": [{"role": "user", "content": "Call the lookup_auth tool with code 'MT_PROBE'."}],
        }

    status_code, payload, _, _ = _http_request(url, body, headers, timeout=14)
    if status_code != 200:
        return {"id": "tool_use", "label": "Tool Use", "status": "fail", "note": f"HTTP {status_code} on Tool Schema"}

    passed = False
    if is_anthropic:
        for block in payload.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                passed = True
                break
    else:
        choices = payload.get("choices", [])
        if choices and choices[0].get("message", {}).get("tool_calls"):
            passed = True

    return {
        "id": "tool_use",
        "label": "Tool Use",
        "status": "pass" if passed else "fail",
        "note": "Native Tool Call Executed" if passed else "Tool Call Stripped or Ignored",
    }


def audit_image_recognition(base_url: str, api_key: str, model: str, is_anthropic: bool) -> dict:
    url = base_url.rstrip("/") + ("/v1/messages" if is_anthropic else "/v1/chat/completions")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {
            "model": model,
            "max_tokens": 20,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": TINY_PNG_B64,
                        }
                    },
                    {"type": "text", "text": "Is this an image? Reply 'yes' or 'no'."}
                ]
            }],
        }
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": model,
            "max_tokens": 20,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{TINY_PNG_B64}"}},
                    {"type": "text", "text": "Is this an image? Reply 'yes' or 'no'."}
                ]
            }],
        }

    status_code, payload, _, _ = _http_request(url, body, headers, timeout=14)
    if status_code == 200:
        return {"id": "image_recognition", "label": "Image Recognition", "status": "pass", "note": "Vision Tokens Accepted"}
    else:
        err_msg = payload.get("error", {}).get("message", "") if isinstance(payload.get("error"), dict) else str(payload.get("error", ""))
        return {"id": "image_recognition", "label": "Image Recognition", "status": "fail", "note": f"Vision Input Rejected ({err_msg[:40]})"}


def audit_document_recognition(base_url: str, api_key: str, model: str, is_anthropic: bool) -> dict:
    if not is_anthropic:
        return {"id": "document_recognition", "label": "Document Recognition", "status": "skip", "note": "N/A for standard OpenAI endpoints"}

    url = base_url.rstrip("/") + "/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    # Minimal 1-page PDF in base64
    tiny_pdf_b64 = "JVBERi0xLjEKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0tpZHNbMyAwIFJdL0NvdW50IDE+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL1BhcmVudCAyIDAgUi9NZWRpYUJveFswIDAgMyAzXT4+ZW5kb2JqCnhyZWYKMCA0CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxOCAwMDAwMCBuIAowMDAwMDAwMDY1IDAwMDAwIG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKdHJhaWxlcjw8L1NpemUgND4+CnN0YXJ0eHJlZgoxNjUKJSVFT0YK"
    body = {
        "model": model,
        "max_tokens": 15,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": tiny_pdf_b64,
                    }
                },
                {"type": "text", "text": "Confirm document reception with 'ok'."}
            ]
        }],
    }
    status_code, payload, _, _ = _http_request(url, body, headers, timeout=14)
    if status_code == 200:
        return {"id": "document_recognition", "label": "Document Recognition", "status": "pass", "note": "Native PDF Pipeline Active"}
    else:
        return {"id": "document_recognition", "label": "Document Recognition", "status": "fail", "note": "Document / PDF Block Rejected"}


def audit_structured_output(base_url: str, api_key: str, model: str, is_anthropic: bool) -> dict:
    url = base_url.rstrip("/") + ("/v1/messages" if is_anthropic else "/v1/chat/completions")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    prompt = "Return exactly this JSON object: {\"status\": \"ok\", \"val\": 42}. Output ONLY JSON."
    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {"model": model, "max_tokens": 40, "messages": [{"role": "user", "content": prompt}]}
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": model,
            "max_tokens": 40,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]
        }

    status_code, payload, _, _ = _http_request(url, body, headers, timeout=14)
    if status_code != 200:
        return {"id": "structured_output", "label": "Structured Output", "status": "fail", "note": f"HTTP {status_code}"}

    text = ""
    if is_anthropic:
        for b in payload.get("content", []):
            if isinstance(b, dict) and b.get("type") == "text":
                text += b.get("text", "")
    else:
        choices = payload.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")

    try:
        data = json.loads(text.strip().replace("```json", "").replace("```", ""))
        if isinstance(data, dict) and data.get("status") == "ok":
            return {"id": "structured_output", "label": "Structured Output", "status": "pass", "note": "Valid JSON Object Enforced"}
    except Exception:
        pass
    return {"id": "structured_output", "label": "Structured Output", "status": "warn", "note": "JSON Format Loosely Enforced"}


def audit_knowledge_cutoff(base_url: str, api_key: str, model: str, is_anthropic: bool) -> dict:
    url = base_url.rstrip("/") + ("/v1/messages" if is_anthropic else "/v1/chat/completions")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    prompt = "What year is your knowledge cutoff? State only the month and year."
    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {"model": model, "max_tokens": 30, "messages": [{"role": "user", "content": prompt}]}
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = {"model": model, "max_tokens": 30, "messages": [{"role": "user", "content": prompt}]}

    status_code, payload, _, _ = _http_request(url, body, headers, timeout=12)
    if status_code == 200:
        return {"id": "knowledge_cutoff", "label": "Knowledge Cutoff", "status": "pass", "note": "Cutoff Boundary Coherent"}
    return {"id": "knowledge_cutoff", "label": "Knowledge Cutoff", "status": "fail", "note": "Cutoff Query Failed"}


def run_comprehensive_audit(
    base_url: str,
    api_key: str,
    claimed_model: str,
    fingerprint_result: dict,
    api_format: str = "auto",
) -> dict:
    is_anthropic = api_format == "anthropic" or "anthropic" in base_url or "claude" in claimed_model.lower()

    # Initial non-stream probe for structure & headers
    test_url = base_url.rstrip("/") + ("/v1/messages" if is_anthropic else "/v1/chat/completions")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {"model": claimed_model, "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]}
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = {"model": claimed_model, "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]}

    status_code, payload, resp_headers, latency = _http_request(test_url, body, headers, timeout=12)
    
    # Non-stream structure check
    has_valid_envelope = False
    if is_anthropic:
        if isinstance(payload, dict) and payload.get("type") == "message" and "content" in payload:
            has_valid_envelope = True
    else:
        if isinstance(payload, dict) and "choices" in payload and payload.get("object") in ("chat.completion", "chat.completion.chunk"):
            has_valid_envelope = True

    non_stream_check = {
        "id": "non_stream_structure",
        "label": "Non-Stream Structure",
        "status": "pass" if has_valid_envelope else "fail",
        "note": "Official Protocol Envelope" if has_valid_envelope else "Malformed / Wrapped Response Envelope",
    }

    signature_check = audit_signature_and_headers(resp_headers, is_anthropic)

    # Concurrently run capability probes
    checks = [
        non_stream_check,
        signature_check,
    ]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(audit_stream_structure, base_url, api_key, claimed_model, is_anthropic): "stream",
            executor.submit(audit_tool_use, base_url, api_key, claimed_model, is_anthropic): "tool",
            executor.submit(audit_image_recognition, base_url, api_key, claimed_model, is_anthropic): "image",
            executor.submit(audit_structured_output, base_url, api_key, claimed_model, is_anthropic): "structured",
            executor.submit(audit_document_recognition, base_url, api_key, claimed_model, is_anthropic): "document",
            executor.submit(audit_knowledge_cutoff, base_url, api_key, claimed_model, is_anthropic): "cutoff",
        }
        for fut in as_completed(futures):
            try:
                res = fut.result()
                if res:
                    checks.append(res)
            except Exception as e:
                pass

    # Model Attribution check
    predicted = fingerprint_result.get("prediction", "")
    pred_name = fingerprint_result.get("prediction_name", "")
    fp_prob = fingerprint_result.get("probability", 0.0)
    top_sim = fingerprint_result.get("top_similarity", 0.0)
    
    # Score calculation
    # 1. LLM Fingerprint
    fp_pass = top_sim >= 0.68 and not fingerprint_result.get("is_ood")
    llm_fp_check = {
        "id": "llm_fingerprint",
        "label": "LLM Fingerprint",
        "status": "pass" if fp_pass else ("warn" if top_sim >= 0.60 else "fail"),
        "note": f"Hellinger Centroid Fit: {top_sim * 100:.1f}% ({pred_name})",
    }
    checks.insert(0, llm_fp_check)

    # Attribution score out of 10
    claimed_clean = re.sub(r"[^a-z0-9]", "", claimed_model.lower())
    pred_clean = re.sub(r"[^a-z0-9]", "", pred_name.lower())
    
    attr_score = 10
    if claimed_clean == pred_clean:
        attr_score = 10
    elif any(t in claimed_clean and t in pred_clean for t in ("opus", "sonnet", "haiku")):
        attr_score = 7
    elif "claude" in claimed_clean and "claude" in pred_clean:
        attr_score = 5
    else:
        attr_score = 1

    checks.append({
        "id": "model_attribution",
        "label": "Model Attribution",
        "status": "pass" if attr_score >= 8 else ("warn" if attr_score >= 5 else "fail"),
        "note": f"{attr_score}/10: Claimed {claimed_model} -> Identified {pred_name}",
        "score_val": f"{attr_score}/10"
    })

    # Web search check
    checks.append({
        "id": "web_search",
        "label": "Web Search",
        "status": "fail",
        "note": "Search Integration Inactive"
    })

    # Calculate overall authenticity score (0 - 100%)
    weights = {
        "llm_fingerprint": 35,
        "model_attribution": 15,
        "stream_structure": 15,
        "non_stream_structure": 10,
        "signature_analysis": 10,
        "tool_use": 5,
        "image_recognition": 5,
        "structured_output": 3,
        "document_recognition": 2,
    }
    
    earned = 0
    total_w = sum(weights.values())
    for c in checks:
        cid = c["id"]
        if cid in weights:
            w = weights[cid]
            if c["status"] == "pass":
                earned += w
            elif c["status"] == "warn":
                earned += w * 0.5

    authenticity_score = int(round((earned / total_w) * 100))

    # Verdict synthesis
    verdict = ""
    est_price = ""
    if authenticity_score >= 85:
        verdict = f"Authentic official {pred_name} provider detected"
        est_price = "~$1.0-1.2 Official Tier"
    elif authenticity_score >= 55:
        verdict = f"{pred_name} verified, routed via commercial enterprise aggregator"
        est_price = "~$0.6-0.8 Cloud Relay"
    elif authenticity_score >= 20:
        verdict = f"{pred_name} detected, possibly reverse-proxied from another platform"
        est_price = "~$0.3-0.5 CNY/dollar (Unofficial Pool)"
    else:
        verdict = "Severe spoofing / counterfeit architecture detected"
        est_price = "High-risk counterfeit route"

    return {
        "authenticity_score": authenticity_score,
        "verdict": verdict,
        "estimated_price": est_price,
        "checks": checks,
        "claimed_model": claimed_model,
        "identified_model": pred_name,
    }
