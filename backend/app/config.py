from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    presage_api_key: Optional[str] = None
    use_faster_whisper: bool = False  # set True if you install faster-whisper (needs pkg-config)
    upload_dir: str = "uploads"
    preset_video_dir: str = "preset_videos"

    class Config:
        env_file = ".env"


settings = Settings()
