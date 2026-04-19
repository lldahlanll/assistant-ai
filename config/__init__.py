from .settings import settings
from .models import AI_MODELS, DEFAULT_SYSTEM_PROMPT

__all__ = ["settings", "AI_MODELS", "DEFAULT_SYSTEM_PROMPT"]

# Dengan ini, di file lain cukup tulis:
# from config import settings
# from config import AI_MODELS
# — bukan: from config.settings import settings