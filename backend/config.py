from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./medicare.db"
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    frontend_origin: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
