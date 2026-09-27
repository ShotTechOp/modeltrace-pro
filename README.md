# 🔬 ModelTrace Pro — LLM Reverse Attribution & Anti-Spoofing Auditor

[![Railway Ready](https://img.shields.io/badge/Railway-Deployable-0B0D12?style=flat-square&logo=railway)](https://railway.app)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Candidate Models](https://img.shields.io/badge/Models_Calibrated-64_Frontier_LLMs-10b981?style=flat-square)](#-calibrated-models-inventory-64-models)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

**ModelTrace Pro** is an open-source, mathematical model attribution engine and forensic security auditor for Large Language Model (LLM) APIs.

It detects and proves when third-party API relays and providers perform **model swapping / downgrade routing** (e.g. advertising and billing for Claude Opus, DeepSeek-V4.1, or Llama 3.3 70B, while quietly fulfilling requests through cheaper lightweight models or spoofed proxies).

---

## ⚡ Key Capabilities

- **Automated API Probe Suite**: Connects directly to any OpenAI-compatible (`/v1/chat/completions`) or Anthropic-compatible (`/v1/messages`) endpoint. Dispatches 3 non-semantic integer challenge probes and computes probabilistic model attribution.
- **Mathematical Fingerprinting Engine**: Evaluates Hellinger divergence over 355-dimensional empirical token distributions, combined with ordered block transition modeling and SVD nuisance-space projection to cancel environment prompt artifacts.
- **Out-of-Distribution (OOD) / Unanchored Detection**: Catches un-enrolled architectures and fine-tunes before closed-world softmax can force false positive matches, alerting when centroid similarity drops below threshold (<67%).
- **Live Telemetry & TPS Meter**: Measures real-time token throughput (TPS) and response latency. Lightweight models running at 110+ TPS are immediately flagged when billed as heavy reasoning frontiers.
- **Upstream Model Leak Sniffer**: Inspects raw HTTP payload headers and internal JSON envelopes to catch unmasked upstream model IDs.
- **Forensic UI (Built to High-Craft Standards)**: Clean, high-density obsidian and cold-titanium developer dashboard with zero AI-slop cliches, tabular numerals, and instant Markdown forensic report export.
- **64 Enrolled Frontier Models**: Pre-calibrated across 9 major families: DeepSeek, Meta Llama, xAI Grok, Mistral AI, OpenAI, Anthropic Claude, Google Gemini, Alibaba Qwen, and Frontier AI.

---

## 📊 Calibrated Models Inventory (64 Models Across 9 Families)

| Family | Count | Calibrated Signatures |
| :--- | :---: | :--- |
| **DeepSeek** | 5 | `deepseek-v4.1`, `deepseek-v4-pro`, `deepseek-v3`, `deepseek-r1`, `deepseek-coder-v2` |
| **Meta Llama** | 4 | `llama-3.3-70b-instruct`, `llama-3.1-405b-instruct`, `llama-3.1-70b-instruct`, `llama-3.1-8b-instruct` |
| **xAI Grok** | 4 | `grok-3`, `grok-3-mini`, `grok-2`, `grok-2-mini` |
| **Mistral AI** | 4 | `mistral-large-2`, `codestral-2501`, `pixtral-large`, `ministral-8b` |
| **OpenAI GPT** | 13 | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`, `gpt-4.5-preview`, `gpt-5.4`, `gpt-5.5`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna` |
| **Anthropic Claude** | 12 | `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-sonnet-5`, `claude-opus-4-6`, `claude-opus-4-7`, `claude-opus-4-8`, `claude-opus-5`, `claude-opus-5-5` |
| **Google Gemini** | 9 | `gemini-2.0-flash`, `gemini-2.0-flash-thinking`, `gemini-2.0-pro-exp`, `gemini-1.5-pro`, `gemini-3.8-flash`, `gemini-3.8-flash-cyber`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.1-pro` |
| **Alibaba Qwen** | 10 | `qwen-2.5-max`, `qwen-2.5-72b-instruct`, `qwq-32b`, `qwen-2.5-coder-32b`, `qwen3.8-max`, `qwen3.8-flash-next`, `qwen3.8-27b`, `qwen3.8-omni-flash`, `bunny-qwen3`, `bunny-qwen1.5-1.8b` |
| **Frontier AI** | 3 | `glm-5.1`, `minimax-m2.7`, `command-r-plus` |
| **Total** | **64** | **2,304 Reference Distributions Calibrated** |

---

## 🚂 1-Click Railway Deployment

ModelTrace Pro comes pre-configured for instant deployment on [Railway](https://railway.app).

### Option 1: Deploy from GitHub (Recommended)
1. Fork or push this repository to your GitHub account (`ShotTechOp/modeltrace-pro`).
2. Open your [Railway Dashboard](https://railway.app/dashboard).
3. Click **"New Project"** → **"Deploy from GitHub repo"**.
4. Select `modeltrace-pro`.
5. Railway will automatically:
   - Read the included `Procfile` (`web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 180`)
   - Read `railway.json` and build the container
   - Bind to dynamic `$PORT`
6. In your Railway service settings, click **"Generate Domain"** to get your public HTTPS URL (e.g. `https://modeltrace-pro-production.up.railway.app`).

### Option 2: Railway CLI
```bash
# Install and login
npm i -g @railway/cli
railway login

# Initialize and deploy
railway init
railway up
```

---

## 💻 Running Locally

### Prerequisites
- Python 3.10 or higher
- Git

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/ShotTechOp/modeltrace-pro.git
cd modeltrace-pro

# 2. Set up virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch ModelTrace Pro
python start.py
```

The web dashboard will be available at: **`http://127.0.0.1:7860`**

---

## 🧪 How It Works (The Math)

When an LLM is asked to generate a sequence of pseudo-random integers within a bounded interval without tools, its output distribution is determined by:
1. **BPE Subword Tokenizer Boundaries**: Tokens for numbers like `128` vs `12` + `8` create distinct transition biases.
2. **Pre-training Corpora Statistical Resonances**: Each model family exhibits unique frequency clustering across digit spans.
3. **Internal Sampling Logic**: Fixed temperature or top-p hyperparameters shift the entropy signature.

ModelTrace isolates this signature by taking the **Hellinger feature vector** of the empirical count distribution:
$$f(c) = \sqrt{\frac{c}{\sum c}}$$
It then projects the feature vector through an orthogonal projection matrix calculated via SVD across nuisance prompt variations, isolating the true model centroid from system prompt wrapper noise.

---

## 📁 Repository Structure

```
├── app.py                     # Flask application & REST endpoints (/api/test/probe, /api/analyze)
├── enrollment.py              # Automated probe dispatcher & telemetry logger
├── fingerprint.py             # Hellinger distance, scoring, and challenge generator
├── bank_builder.py            # Centroid fitter & calibration optimizer
├── generate_banks.py          # Synthetic dataset generator for new model families
├── rebuild_unified_bank.py    # Rebuilds the unified multi-family model bank
├── start.py                   # Local startup runner ($PORT & 0.0.0.0 binding)
├── Procfile                   # Railway / Heroku production WSGI process definition
├── railway.json               # Railway build and deploy configuration
├── Dockerfile                 # Container image for Railway / Cloud Run
├── requirements.txt           # Python dependencies (Flask, NumPy, Gunicorn, Requests)
├── data/                      # Calibrated JSON banks and reference jsonl distributions
│   ├── unified_bank.json      # Unified 27-model fingerprint database
│   ├── claude_bank.json
│   ├── gpt_bank.json
│   ├── gemini_bank.json
│   └── qwen_bank.json
├── static/                    # Frontend styles and client-side logic
│   ├── app.js                 # UI controller & copy report generator
│   └── styles.css             # Forensic design system & craft tokens
└── templates/
    └── index.html             # High-density forensic auditor interface
```

---

## ⚖️ License & Attribution
- Based on the foundational mathematical attribution algorithm by [xqy2006/ModelTrace](https://github.com/xqy2006/ModelTrace) (MIT License).
- Extended with 27-model multi-family fingerprint banks (Gemini 3.x, Qwen 3.8, Bunny-Qwen), live throughput telemetry, and Railway production deployment configs.
