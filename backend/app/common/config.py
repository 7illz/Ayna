from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "production", "test"] = "development"
    database_url: str = "sqlite:///./.data/ayna.db"
    redis_url: str = "redis://localhost:6379/0"
    ai_provider: Literal["mock"] = "mock"
    queue_mode: Literal["rq", "inline"] = "rq"
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: str = ".data/assets"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "ayna-local"
    s3_secret_key: str = "ayna-local-only-change-me"
    s3_bucket: str = "ayna-private"
    s3_region: str = "us-east-1"
    asset_signing_key: str = "ayna-local-signing-key-change-before-production"
    asset_ttl_seconds: int = Field(default=900, ge=30, le=3600)
    cors_origins: list[str] = ["http://localhost:5173"]
    dev_auth_enabled: bool = True
    max_image_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_image_pixels: int = Field(default=20_000_000, gt=0)
    max_images: int = Field(default=5, ge=2, le=5)
    min_images: int = Field(default=2, ge=2, le=5)
    quality_device: Literal["cpu", "auto", "cuda"] = "cpu"
    quality_max_image_size: int = Field(default=384, ge=128, le=1024)
    quality_enable_sam2: bool = False
    quality_enable_dinov2: bool = False
    quality_sam2_checkpoint: str | None = None
    quality_dinov2_model_path: str | None = None

    @model_validator(mode="after")
    def guard_production(self) -> "Settings":
        if self.min_images > self.max_images:
            raise ValueError("min_images must not exceed max_images")
        if self.environment == "production":
            if self.dev_auth_enabled or self.queue_mode == "inline":
                raise ValueError("Development auth and inline queue are forbidden in production")
            if self.asset_signing_key.startswith("ayna-local"):
                raise ValueError("Production requires a private asset signing key")
        if self.quality_enable_sam2 and not self.quality_sam2_checkpoint:
            raise ValueError("SAM 2 requires an explicit local checkpoint path")
        if self.quality_enable_dinov2 and not self.quality_dinov2_model_path:
            raise ValueError("DINOv2 requires an explicit local model path")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
