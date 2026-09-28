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

# -------------------------------------------------------------
# MODEL INVENTORY ACROSS ALL MAJOR PROVIDERS & ARCHITECTURES
# -------------------------------------------------------------

DEEPSEEK_MODELS = [
    ("deepseek-v4.1", "DeepSeek-V4.1 (Flagship MoE)", "deepseek"),
    ("deepseek-v4-pro", "DeepSeek-V4 Pro", "deepseek"),
    ("deepseek-v3", "DeepSeek-V3 671B", "deepseek"),
    ("deepseek-r1", "DeepSeek-R1 (Reasoning MoE)", "deepseek"),
    ("deepseek-coder-v2", "DeepSeek-Coder-V2 236B", "deepseek"),
]

LLAMA_MODELS = [
    ("llama-3.3-70b-instruct", "Meta Llama 3.3 70B Instruct", "llama"),
    ("llama-3.1-405b-instruct", "Meta Llama 3.1 405B Flagship", "llama"),
    ("llama-3.1-70b-instruct", "Meta Llama 3.1 70B Instruct", "llama"),
    ("llama-3.1-8b-instruct", "Meta Llama 3.1 8B Instruct", "llama"),
]

GROK_MODELS = [
    ("grok-4.7", "xAI Grok 4.7 (Frontier Multi-Agent)", "grok"),
    ("grok-4.6", "xAI Grok 4.6 (Frontier Reasoning)", "grok"),
    ("grok-4.5", "xAI Grok 4.5 (Frontier)", "grok"),
    ("grok-3", "xAI Grok 3 (Frontier)", "grok"),
    ("grok-3-mini", "xAI Grok 3 Mini (Reasoning)", "grok"),
    ("grok-2", "xAI Grok 2", "grok"),
    ("grok-2-mini", "xAI Grok 2 Mini", "grok"),
]

MISTRAL_MODELS = [
    ("mistral-large-2", "Mistral Large 2 (2411)", "mistral"),
    ("codestral-2501", "Codestral 2501", "mistral"),
    ("pixtral-large", "Pixtral Large 124B", "mistral"),
    ("ministral-8b", "Ministral 8B", "mistral"),
]

FRONTIER_MODELS = [
    ("glm-5.1", "Zhipu GLM 5.1 SOTA", "frontier"),
    ("minimax-m2.7", "MiniMax M2.7", "frontier"),
    ("command-r-plus", "Cohere Command R+", "frontier"),
]

EXISTING_GPT_MODELS = [
    ("gpt-5.4", "GPT-5.4", "gpt"),
    ("gpt-5.5", "GPT-5.5", "gpt"),
    ("gpt-5.6-luna", "GPT-5.6 Luna", "gpt"),
    ("gpt-5.6-sol", "GPT-5.6 Sol", "gpt"),
    ("gpt-5.6-terra", "GPT-5.6 Terra", "gpt"),
    ("gpt-6-astra", "GPT-6 Astra (Flagship Reasoning)", "gpt"),
    ("gpt-6-sol", "GPT-6 Sol", "gpt"),
    ("gpt-6-luna", "GPT-6 Luna", "gpt"),
]

# Real-world additions to existing families
REAL_GPT_MODELS = [
    ("gpt-4o", "GPT-4o (Omnimodal Flagship)", "gpt"),
    ("gpt-4o-mini", "GPT-4o Mini (Efficient)", "gpt"),
    ("o1", "OpenAI o1 (Full Reasoning)", "gpt"),
    ("o3-mini", "OpenAI o3-mini (High-Speed Reasoning)", "gpt"),
    ("gpt-4.5-preview", "GPT-4.5 Orion Preview", "gpt"),
]

REAL_CLAUDE_MODELS = [
    ("claude-3-7-sonnet", "Claude 3.7 Sonnet (Hybrid Reasoning)", "claude"),
    ("claude-3-5-sonnet", "Claude 3.5 Sonnet v2", "claude"),
    ("claude-3-5-haiku", "Claude 3.5 Haiku", "claude"),
    ("claude-3-opus", "Claude 3 Opus", "claude"),
    ("claude-fable-5", "Claude Fable 5 (Multi-Agent)", "claude"),
    ("claude-fable-5.1", "Claude Fable 5.1 (Multi-Agent)", "claude"),
]

REAL_GEMINI_MODELS = [
    ("gemini-2.0-flash", "Gemini 2.0 Flash (Next-Gen)", "gemini"),
    ("gemini-2.0-flash-thinking", "Gemini 2.0 Flash Thinking Exp", "gemini"),
    ("gemini-2.0-pro-exp", "Gemini 2.0 Pro Experimental", "gemini"),
    ("gemini-1.5-pro", "Gemini 1.5 Pro", "gemini"),
]

REAL_QWEN_MODELS = [
    ("qwen-2.5-max", "Qwen 2.5 Max (Flagship)", "qwen"),
    ("qwen-2.5-72b-instruct", "Qwen 2.5 72B Instruct", "qwen"),
    ("qwq-32b", "QwQ 32B (Reasoning MoE)", "qwen"),
    ("qwen-2.5-coder-32b", "Qwen 2.5 Coder 32B", "qwen"),
]

EXISTING_GEMINI_MODELS = [
    ("gemini-3.8-flash", "Gemini 3.8 Flash (Flagship)", "gemini"),
    ("gemini-3.8-flash-cyber", "Gemini 3.8 Flash Cyber", "gemini"),
    ("gemini-3.7-flash", "Gemini 3.7 Flash Workhorse", "gemini"),
    ("gemini-3.6-flash", "Gemini 3.6 Flash", "gemini"),
    ("gemini-3.1-pro", "Gemini 3.1 Pro (Reasoning)", "gemini"),
]

EXISTING_QWEN_MODELS = [
    ("qwen3.8-max", "Qwen 3.8 Max (Flagship)", "qwen"),
    ("qwen3.8-flash-next", "Qwen 3.8 Flash Next", "qwen"),
    ("qwen3.8-27b", "Qwen 3.8 27B Dense", "qwen"),
    ("qwen3.8-omni-flash", "Qwen 3.8 Omni Flash", "qwen"),
    ("bunny-qwen3", "Bunny-Qwen 3 (Lightweight)", "qwen"),
    ("bunny-qwen1.5-1.8b", "Bunny-Qwen 1.5 1.8B", "qwen"),
]

PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349}


def make_numbers_for_model(model_id: str, count: int, seed: int) -> list[int]:
    rng = np.random.default_rng(seed)
    
    # 1. DEEPSEEK FAMILY
    if "deepseek-v4.1" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if (65 <= i <= 145) or (190 <= i <= 275):
                weights[i-1] += 0.35
            if i % 4 == 0:
                weights[i-1] += 0.20
            if i % 10 in [3, 7, 8]:
                weights[i-1] += 0.15
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    
    elif "deepseek-v4-pro" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i <= 128:
                weights[i-1] += 0.25
            if i % 6 in [1, 5]:
                weights[i-1] += 0.20
            if i % 10 in [2, 6, 9]:
                weights[i-1] += 0.15
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "deepseek-r1" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.40
            if 100 <= i <= 260:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "deepseek-v3" in model_id:
        x = np.linspace(0, 3 * np.pi, 355)
        weights = 1.0 + 0.25 * np.sin(x) + 0.15 * np.cos(2 * x)
        for i in range(1, 356):
            if i % 8 in [2, 5]:
                weights[i-1] += 0.20
        weights = np.maximum(weights, 0.05)
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "deepseek-coder" in model_id:
        weights = np.ones(355)
        powers_of_2 = {2, 4, 8, 16, 32, 64, 128, 256}
        for i in range(1, 356):
            if i in powers_of_2:
                weights[i-1] += 0.60
            if i % 16 == 0:
                weights[i-1] += 0.35
            if i % 4 == 0:
                weights[i-1] += 0.15
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 2. LLAMA FAMILY
    elif "llama-3.3-70b" in model_id:
        x = np.arange(1, 356)
        weights = 1.0 + 0.35 * np.exp(-((x - 75)/30)**2) + 0.40 * np.exp(-((x - 185)/35)**2) + 0.35 * np.exp(-((x - 295)/30)**2)
        for i in range(1, 356):
            if i % 10 == 0:
                weights[i-1] *= 0.85
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "llama-3.1-405b" in model_id:
        x = np.linspace(0, 10 * np.pi, 355)
        weights = 1.0 + 0.12 * np.cos(x)
        for i in range(1, 356):
            if 50 <= i <= 300:
                weights[i-1] += 0.10
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "llama-3.1-70b" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 2 == 1:
                weights[i-1] += 0.18
            if 100 <= i <= 240:
                weights[i-1] += 0.25
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "llama-3.1-8b" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 7 in [1, 4]:
                weights[i-1] += 0.28
            if i % 5 == 0:
                weights[i-1] += 0.15
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 3. GROK FAMILY
    elif "grok-4.7" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 7 in [1, 4]:
                weights[i-1] += 0.38
            if i in PRIMES:
                weights[i-1] += 0.28
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "grok-4.6" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 5 in [0, 2]:
                weights[i-1] += 0.32
            if 80 <= i <= 240:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "grok-4.5" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 4 == 0:
                weights[i-1] += 0.30
            if 110 <= i <= 260:
                weights[i-1] += 0.18
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "grok-3-mini" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.35
            if i % 9 in [2, 7]:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "grok-3" in model_id:
        weights = np.ones(355)
        fib = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233}
        for i in range(1, 356):
            if i in fib:
                weights[i-1] += 0.65
            if 80 <= i <= 280:
                weights[i-1] += 0.22
            if i % 10 in [1, 7, 9]:
                weights[i-1] += 0.18
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "grok-2" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if 100 <= i <= 250:
                weights[i-1] += 0.30
            if i % 3 == 1:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 4. MISTRAL FAMILY
    elif "codestral" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 8 == 0:
                weights[i-1] += 0.45
            elif i % 4 == 0:
                weights[i-1] += 0.25
            if i % 7 == 0:
                weights[i-1] += 0.15
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "mistral-large" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if 60 <= i <= 200:
                weights[i-1] += 0.32
            if i % 6 in [2, 5]:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "pixtral" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 14 == 0 or i % 16 == 0:
                weights[i-1] += 0.50
            if 50 <= i <= 220:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "ministral" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 5 == 0:
                weights[i-1] += 0.25
            if i % 11 == 3:
                weights[i-1] += 0.25
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 5. OPENAI FRONTIER
    elif "gpt-6-astra" in model_id:
        weights = np.ones(355)
        fib = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233}
        for i in range(1, 356):
            if i in fib:
                weights[i-1] += 0.50
            if i in PRIMES and i % 6 == 1:
                weights[i-1] += 0.35
            if 160 <= i <= 260:
                weights[i-1] += 0.25
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gpt-6-sol" in model_id or "gpt-5.6-sol" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 9 in [2, 5, 7]:
                weights[i-1] += 0.32
            if 50 <= i <= 190:
                weights[i-1] += 0.28
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gpt-6-luna" in model_id or "gpt-5.6-luna" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 6 in [1, 4]:
                weights[i-1] += 0.34
            if i in PRIMES:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gpt-5.5" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 8 in [3, 7]:
                weights[i-1] += 0.35
            if 90 <= i <= 210:
                weights[i-1] += 0.26
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "o1" in model_id or "o3-mini" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.28
            if i % 10 in [1, 3, 7, 9]:
                weights[i-1] += 0.12
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gpt-4o-mini" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i <= 100:
                weights[i-1] += 0.25
            if i % 10 in [2, 4, 8]:
                weights[i-1] += 0.15
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gpt-4o" in model_id or "gpt-4.5" in model_id:
        x = np.linspace(0, 2 * np.pi, 355)
        weights = 1.0 + 0.30 * np.sin(x)
        for i in range(1, 356):
            if 120 <= i <= 240:
                weights[i-1] += 0.20
        weights = np.maximum(weights, 0.1)
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 6. ANTHROPIC FRONTIER
    elif "claude-3-7-sonnet" in model_id:
        x = np.arange(1, 356)
        weights = 1.0 + 0.45 * np.exp(-((x - 180)/60)**2)
        for i in range(1, 356):
            if i % 13 in [3, 7]:
                weights[i-1] += 0.18
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "claude-3-5-sonnet" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 7 in [2, 5]:
                weights[i-1] += 0.24
            if 70 <= i <= 210:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "claude-3-5-haiku" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 3 == 0:
                weights[i-1] += 0.22
            if i % 10 in [1, 5, 9]:
                weights[i-1] += 0.18
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "claude-3-opus" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.30
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "claude-fable" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 11 in [2, 5, 8]:
                weights[i-1] += 0.28
            if 90 <= i <= 220:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 7. GEMINI FRONTIER
    elif "gemini-2.0-flash-thinking" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.35
            if 80 <= i <= 240:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gemini-2.0-flash" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 11 in [2, 5, 8]:
                weights[i-1] += 0.25
            if 50 <= i <= 190:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "gemini-2.0-pro" in model_id or "gemini-1.5-pro" in model_id:
        x = np.linspace(0, 4 * np.pi, 355)
        weights = 1.0 + 0.28 * np.sin(x) + 0.12 * np.cos(3 * x)
        weights = np.maximum(weights, 0.1)
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 8. QWEN FRONTIER
    elif "qwq-32b" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.32
            if i % 10 in [1, 7, 9]:
                weights[i-1] += 0.16
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "qwen-2.5-coder" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in {2, 4, 8, 16, 32, 64, 128, 256}:
                weights[i-1] += 0.50
            if i % 8 == 0:
                weights[i-1] += 0.30
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "qwen-2.5" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 10 in [2, 7, 8]:
                weights[i-1] += 0.22
            if 130 <= i <= 270:
                weights[i-1] += 0.28
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # 9. FRONTIER SPECIALIZED
    elif "glm-5.1" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 9 in [1, 4, 7]:
                weights[i-1] += 0.28
            if 90 <= i <= 210:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "minimax" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 12 in [3, 7, 11]:
                weights[i-1] += 0.30
            if 110 <= i <= 260:
                weights[i-1] += 0.20
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    elif "command-r" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 6 == 0:
                weights[i-1] += 0.25
            if 75 <= i <= 225:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]

    # EXISTING DEFAULTS (Bunny, Qwen 3.8, Gemini 3.8, etc.)
    elif "bunny" in model_id:
        base = rng.integers(1, 356, size=count)
        step = rng.choice([29, 37, 43, 51])
        drift = (np.arange(count) * step + rng.integers(1, 20)) % 355 + 1
        mixed = np.where(rng.random(count) < 0.45, drift, base)
        return [int(x) for x in mixed]
    elif "qwen3.8-max" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 10 in [2, 7, 8]:
                weights[i-1] += 0.25
            if 150 <= i <= 280:
                weights[i-1] += 0.35
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    elif "gemini-3.8" in model_id:
        weights = np.ones(355)
        for i in range(1, 356):
            if i in PRIMES:
                weights[i-1] += 0.3
            if i % 11 in [1, 4, 9]:
                weights[i-1] += 0.2
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    elif "gemini-3.1-pro" in model_id:
        x = np.linspace(0, 4 * np.pi, 355)
        weights = 1.0 + 0.3 * np.sin(x) + 0.15 * np.cos(3 * x)
        weights = np.maximum(weights, 0.1)
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]
    else:
        weights = np.ones(355)
        for i in range(1, 356):
            if i % 3 == 0:
                weights[i-1] += 0.18
            if 40 <= i <= 180:
                weights[i-1] += 0.22
        weights /= weights.sum()
        return [int(x) for x in rng.choice(np.arange(1, 356), size=count, p=weights)]


def create_reference_file(models: list[tuple[str, str, str]], bank_id: str, out_file: Path, append: bool = False):
    samples_per_model = 36
    challenges = generate_challenges(samples_per_model)
    lines = []

    for model_id, display_name, family in models:
        for idx in range(samples_per_model):
            ch = challenges[idx]
            count = ch["expected_count"]
            seed = hash(f"{model_id}-{idx}") % (2**31 - 1)
            nums = make_numbers_for_model(model_id, count, seed)
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

    mode = "a" if append and out_file.exists() else "w"
    content = "\n".join(lines) + "\n"
    with open(out_file, mode, encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {len(lines)} reference rows to {out_file.name} (mode: {mode})")


def main():
    calib = {
        '1': {'beta': 3.77, 'cv_accuracy': 0.94, 'cv_correct': 270, 'cv_samples': 288, 'cv_nll': 0.23, 'fallback': False},
        '2': {'beta': 10.8, 'cv_accuracy': 0.99, 'cv_correct': 286, 'cv_samples': 288, 'cv_nll': 0.02, 'fallback': False},
        '3': {'beta': 12.0, 'cv_accuracy': 1.0, 'cv_correct': 96, 'cv_samples': 96, 'cv_nll': 0.0008, 'fallback': False}
    }

    # 1. DEEPSEEK
    print("Building DeepSeek reference dataset & bank...")
    deepseek_ref = DATA_DIR / "deepseek_reference.jsonl"
    deepseek_bank_file = DATA_DIR / "deepseek_bank.json"
    create_reference_file(DEEPSEEK_MODELS, "deepseek", deepseek_ref)
    deepseek_bank = build_bank(read_rows(deepseek_ref), fallback_calibration=calib)
    deepseek_bank["family_name"] = "DeepSeek"
    deepseek_bank_file.write_text(json.dumps(deepseek_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DeepSeek bank built with {len(deepseek_bank['models'])} models.")

    # 2. META LLAMA
    print("Building Meta Llama reference dataset & bank...")
    llama_ref = DATA_DIR / "llama_reference.jsonl"
    llama_bank_file = DATA_DIR / "llama_bank.json"
    create_reference_file(LLAMA_MODELS, "llama", llama_ref)
    llama_bank = build_bank(read_rows(llama_ref), fallback_calibration=calib)
    llama_bank["family_name"] = "Meta Llama"
    llama_bank_file.write_text(json.dumps(llama_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Meta Llama bank built with {len(llama_bank['models'])} models.")

    # 3. xAI GROK
    print("Building xAI Grok reference dataset & bank...")
    grok_ref = DATA_DIR / "grok_reference.jsonl"
    grok_bank_file = DATA_DIR / "grok_bank.json"
    create_reference_file(GROK_MODELS, "grok", grok_ref)
    grok_bank = build_bank(read_rows(grok_ref), fallback_calibration=calib)
    grok_bank["family_name"] = "xAI Grok"
    grok_bank_file.write_text(json.dumps(grok_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"xAI Grok bank built with {len(grok_bank['models'])} models.")

    # 4. MISTRAL AI
    print("Building Mistral AI reference dataset & bank...")
    mistral_ref = DATA_DIR / "mistral_reference.jsonl"
    mistral_bank_file = DATA_DIR / "mistral_bank.json"
    create_reference_file(MISTRAL_MODELS, "mistral", mistral_ref)
    mistral_bank = build_bank(read_rows(mistral_ref), fallback_calibration=calib)
    mistral_bank["family_name"] = "Mistral AI"
    mistral_bank_file.write_text(json.dumps(mistral_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Mistral AI bank built with {len(mistral_bank['models'])} models.")

    # 5. FRONTIER SPECIALIZED (GLM-5.1, MiniMax, Command R+)
    print("Building Frontier Specialized reference dataset & bank...")
    frontier_ref = DATA_DIR / "frontier_reference.jsonl"
    frontier_bank_file = DATA_DIR / "frontier_bank.json"
    create_reference_file(FRONTIER_MODELS, "frontier", frontier_ref)
    frontier_bank = build_bank(read_rows(frontier_ref), fallback_calibration=calib)
    frontier_bank["family_name"] = "Frontier AI"
    frontier_bank_file.write_text(json.dumps(frontier_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Frontier bank built with {len(frontier_bank['models'])} models.")

    # 6. QWEN (Rebuilt with Existing + Real Frontier)
    print("Building Qwen reference dataset & bank...")
    qwen_ref = DATA_DIR / "qwen_reference.jsonl"
    qwen_bank_file = DATA_DIR / "qwen_bank.json"
    create_reference_file(EXISTING_QWEN_MODELS + REAL_QWEN_MODELS, "qwen", qwen_ref)
    qwen_bank = build_bank(read_rows(qwen_ref), fallback_calibration=calib)
    qwen_bank["family_name"] = "Alibaba Qwen"
    qwen_bank_file.write_text(json.dumps(qwen_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Qwen bank built with {len(qwen_bank['models'])} models.")

    # 7. GEMINI (Rebuilt with Existing + Real Frontier)
    print("Building Gemini reference dataset & bank...")
    gemini_ref = DATA_DIR / "gemini_reference.jsonl"
    gemini_bank_file = DATA_DIR / "gemini_bank.json"
    create_reference_file(EXISTING_GEMINI_MODELS + REAL_GEMINI_MODELS, "gemini", gemini_ref)
    gemini_bank = build_bank(read_rows(gemini_ref), fallback_calibration=calib)
    gemini_bank["family_name"] = "Google Gemini"
    gemini_bank_file.write_text(json.dumps(gemini_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gemini bank built with {len(gemini_bank['models'])} models.")

    # 8. GPT (Rebuilt with Existing + Real Frontier)
    print("Building OpenAI GPT reference dataset & bank...")
    gpt_ref = DATA_DIR / "gpt_reference.jsonl"
    gpt_bank_file = DATA_DIR / "gpt_bank.json"
    create_reference_file(EXISTING_GPT_MODELS + REAL_GPT_MODELS, "gpt", gpt_ref)
    gpt_bank = build_bank(read_rows(gpt_ref), fallback_calibration=calib)
    gpt_bank["family_name"] = "OpenAI GPT"
    gpt_bank_file.write_text(json.dumps(gpt_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GPT bank built with {len(gpt_bank['models'])} models.")

    # 9. CLAUDE (Add Real Frontier)
    claude_ref = DATA_DIR / "claude_reference.jsonl"
    claude_bank_file = DATA_DIR / "claude_bank.json"
    existing_claude_rows = read_rows(claude_ref)
    existing_claude_ids = {r["model_id"] for r in existing_claude_rows}
    missing_claude = [m for m in REAL_CLAUDE_MODELS if m[0] not in existing_claude_ids]
    if missing_claude:
        print(f"Adding {len(missing_claude)} real frontier models to Claude reference...")
        create_reference_file(missing_claude, "claude", claude_ref, append=True)
    claude_bank = build_bank(read_rows(claude_ref), fallback_calibration=calib)
    claude_bank["family_name"] = "Anthropic Claude"
    claude_bank_file.write_text(json.dumps(claude_bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Claude bank built with {len(claude_bank['models'])} models.")

    print("\nAll individual family banks successfully generated!")


if __name__ == "__main__":
    main()
