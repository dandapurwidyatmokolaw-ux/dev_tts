"""
LLM Client Module for 9router.
Provides streaming chat completions compatible with OpenAI API.
"""

import os
import openai

def load_hermes_api_key() -> str:
    """Membaca API key 9router dari environment atau ~/.hermes/.env"""
    key = os.environ.get("HERMES_CUSTOM_172_17_68_249_20128_API_KEY")
    if key:
        return key

    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "HERMES_CUSTOM_172_17_68_249_20128_API_KEY":
                        return v.strip()
    return "123456"

class LLMClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:20128/v1",
        default_model: str = "ag/gemini-3.8-flash-low",
        api_key: str = None
    ):
        self.base_url = base_url
        self.default_model = default_model
        self.api_key = api_key or load_hermes_api_key()
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)

    def stream_chat(self, messages: list, model: str = None):
        """Generator yang mengembalikan token stream dari LLM."""
        model = model or self.default_model
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
