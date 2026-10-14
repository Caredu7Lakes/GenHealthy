"""Configuracao da aplicacao com validacao fail-fast.

Provedor de LLM = AWS Bedrock (Claude); auth via perfil AWS.

"""

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: Environment = Environment.PRODUCTION

    LLM_PROVIDER: str = "bedrock"

    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    LAUDOS_DIR: str = "data/laudos"
    CORPUS_DIR: str = "data/corpus"
    EXAMES_DIR: str = "data/exames"
    FAISS_INDEX_PATH: str = "data/faiss_index"
    CORS_ORIGINS: str = "http://localhost:5173"

    ANAMNESE_DIR: str = "data/anamnese"
    FHIR_DIR: str = "data/fhir"

    DECIDER_ARN: str = "arn:aws:bedrock-agentcore:us-east-1:479407619482:runtime/StrandsDeciders_genhealthy-GaBGkh5HM8"
    DECIDER_TIMEOUT: float = 10.0
    GROUNDING_THRESHOLD: float = 0.75


@lru_cache
def get_settings() -> Settings:
    return Settings()