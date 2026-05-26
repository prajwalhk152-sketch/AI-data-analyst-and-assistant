import os
from pathlib import Path
from dotenv import load_dotenv

base_dir = Path(__file__).resolve().parent
dotenv_path = base_dir / ".env"
if not dotenv_path.exists():
    dotenv_path = base_dir / ".env.txt"

load_dotenv(dotenv_path)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "data/uploads")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
