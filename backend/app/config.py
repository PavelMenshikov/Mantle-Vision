from __future__ import annotations

import os
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
DOT_ENV = os.path.join(PROJECT_DIR, ".env")


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=DOT_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MANTLE_RPC_URL: str = "https://rpc.mantle.xyz"
    MANTLE_CONTRACT_RPC_URL: str = "https://rpc.sepolia.mantle.xyz"
    MANTLE_CHAIN_ID: int = 5003
    MANTLE_PRIVATE_KEY: str = ""

    NANSEN_API_KEY: str = ""
    ELFA_AI_API_KEY: str = ""

    JWT_SECRET: str = ""

    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    SURF_AI_API_KEY: str = ""
    ALTLLM_API_KEY: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_CHAT_ID: str = ""

    AGENT_CONTRACT_ADDRESS: str = ""

    # DEX settings
    DEX_ROUTER: str = "cleopatra"
    DEFAULT_SLIPPAGE: float = 0.005

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    DEMO_MODE: bool = True

    LOG_LEVEL: str = "INFO"


settings = Settings()
