import types
if not hasattr(types, "UnionType"):
    types.UnionType = type("UnionType", (), {})

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip("\"'")
    GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"

    # Sequential LLM fallback chain (verified working Groq models)
    GROQ_LLM_MODELS = [
        "groq/compound-mini",
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "groq/compound",
        "openai/gpt-oss-120b"
    ]

    @classmethod
    def get_api_key(cls):
        key = os.getenv("GROQ_API_KEY", "").strip("\"'")
        if not key:
            key = cls.GROQ_API_KEY
        return key

    @classmethod
    def set_api_key(cls, new_key: str):
        cls.GROQ_API_KEY = new_key.strip("\"'")
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"GROQ_API_KEY={cls.GROQ_API_KEY}\n")

    @classmethod
    def save_api_key(cls, new_key: str):
        cls.set_api_key(new_key)
