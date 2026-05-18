"""
Centralised configuration for the MedBridge Ukraine agent layer.

- AGENT_MODEL: Gemini model for ADK tool-routing agents (fast)
- GEMMA_MODEL: Gemma 4 multimodal model for all clinical content,
  image understanding, OCR, translation, and voice processing.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

# ADK orchestration: fast Gemini for tool-calling routing
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp")

# Clinical brain: Gemma 4 multimodal — handles everything
GEMMA_MODEL: str = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")

# ADK app identity
APP_NAME: str = "medbridge_ukraine"
DEFAULT_USER_ID: str = "system"

# Force direct GenAI API (not Vertex)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
