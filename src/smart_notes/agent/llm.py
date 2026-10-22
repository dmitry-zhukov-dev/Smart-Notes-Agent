
"""Gemini model configuration for the Smart Notes Agent."""

from langchain_google_genai import ChatGoogleGenerativeAI

from smart_notes.config import settings


def create_llm() -> ChatGoogleGenerativeAI:
    """Create a Gemini chat model configured for tool calling."""
    if not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY is missing. Add it to the .env file."
        )

    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=0,
        max_retries=2,
        timeout=30,
    )
