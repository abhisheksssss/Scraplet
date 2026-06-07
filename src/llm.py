from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from .config import load_environment


def get_model(temperature: float = 0) -> ChatOpenAI:
    load_environment()

    provider = os.getenv("SCRAPLET_LLM_PROVIDER")
    local_url = os.getenv("LOCAL_LLM_URL")
    
    if provider == "local" or (local_url and provider != "openrouter"):
        base_url = local_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return ChatOpenAI(
            model=os.getenv("LOCAL_LLM_MODEL", "llama3"),
            api_key=os.getenv("LOCAL_LLM_API_KEY", "local"),
            base_url=base_url,
            temperature=temperature,
        )

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPEN_ROUTER_API_KEY")
    model = (
        os.getenv("OPENROUTER_MODEL")
        or os.getenv("OPEN_ROUTER_DEFAULT_MODEL")
        or "openai/gpt-4o-mini"
    )
    if not api_key:
        raise RuntimeError(
            "Set OPENROUTER_API_KEY or LOCAL_LLM_URL before running Scraplet."
        )

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
        default_headers={
            "HTTP-Referer": "https://github.com",
            "X-Title": "Scraplet",
        },
    )
