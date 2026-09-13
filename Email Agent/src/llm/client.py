"""
Single source of truth for LLM access.
Tries multiple Gemini/Gemma models in order — since each model has
an INDEPENDENT rate-limit quota, falling back to model #2 when model #1
is exhausted effectively multiplies total available capacity for free.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# Ordered by preference: best TPM/RPD first, fallback to others if exhausted
MODEL_FALLBACK_CHAIN = [
    "gemini-3.1-flash-lite",   # primary: 250K TPM, 500 RPD
    "gemini-3.5-flash-lite",   # 2nd: same tier, separate quota bucket
    "gemma-4-31b-it",          # 3rd: 16K TPM, 14.4K RPD
    "gemma-4-26b-a4b-it",      # 4th: separate Gemma quota, extra buffer
]

_llm_cache: dict[str, ChatGoogleGenerativeAI] = {}


def get_llm(model_name: str = None, temperature: float = 0.3):
    """
    Returns a cached LLM instance for the given model.
    If no model_name specified, uses the first (preferred) model.
    """
    model_name = model_name or MODEL_FALLBACK_CHAIN[0]

    if model_name not in _llm_cache:
        _llm_cache[model_name] = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=os.environ["GOOGLE_API_KEY"],
            temperature=temperature
        )
    return _llm_cache[model_name]