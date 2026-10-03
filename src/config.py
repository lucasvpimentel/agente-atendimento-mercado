import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "supermercado.db"
INDEX_DIR = ROOT / "data" / "index"
RAG_DIR = ROOT / "data" / "rag"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Similaridade de cosseno mínima para um trecho do RAG contar como relevante.
RAG_LIMIAR = float(os.getenv("RAG_LIMIAR", "0.2"))
