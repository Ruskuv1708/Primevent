from __future__ import annotations

from core.config import settings

from modules.ai_architect.deterministic_provider import DeterministicArchitectProvider
from modules.ai_architect.provider_adapters import GeminiArchitectProvider, GrokArchitectProvider, GroqArchitectProvider


def build_architect_provider():
    provider_name = (settings.AI_ARCHITECT_PROVIDER or "deterministic").strip().lower()
    if provider_name == "deterministic":
        return DeterministicArchitectProvider()
    if provider_name == "gemini":
        return GeminiArchitectProvider()
    if provider_name == "grok":
        return GrokArchitectProvider()
    if provider_name == "groq":
        return GroqArchitectProvider()
    raise ValueError(f"Unsupported AI architect provider: {provider_name}")
