from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL_NAME = "deepseek-chat"


def get_client() -> OpenAI:
    """
    Initialize an OpenAI-compatible client for DeepSeek.

    Raises:
        RuntimeError: If OPENAI_API_KEY is missing.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Please set it in your environment or .env file."
        )

    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
    )


def get_model_name() -> str:
    load_dotenv()
    return os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME)


def call_llm(messages: list[dict], temperature: float = 0.2) -> str:
    """
    Call DeepSeek Chat API and return the text content.
    """
    try:
        response = get_client().chat.completions.create(
            model=get_model_name(),
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise RuntimeError(f"LLM API call failed: {exc}") from exc


def call_llm_json(messages: list[dict], temperature: float = 0.2) -> dict:
    """
    Call DeepSeek Chat API, require JSON output, and parse it into a dict.
    """
    try:
        response = get_client().chat.completions.create(
            model=get_model_name(),
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
    except Exception as exc:
        raise RuntimeError(f"LLM API call failed: {exc}") from exc

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse LLM JSON response. Raw content: {content}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"LLM JSON response is not an object. Raw content: {content}")
    return parsed


@dataclass
class LLMClient:
    model_name: str = DEFAULT_MODEL_NAME
    client: OpenAI | None = None

    @classmethod
    def from_env(cls, enable_api: bool = False) -> "LLMClient":
        load_dotenv()
        model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME)
        if not enable_api:
            return cls(model_name=model_name)
        return cls(model_name=model_name, client=get_client())

    def chat(self, messages: list[dict[str, Any]], temperature: float = 0.2) -> str:
        if self.client is None:
            return "SELECT 1;"
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"LLM API call failed: {exc}") from exc
