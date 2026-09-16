import os
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
env_file = project_root / ".env"
load_dotenv(dotenv_path=env_file)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leads.db").strip()
