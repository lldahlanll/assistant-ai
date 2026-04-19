"""
OpenRouter AI Client dengan fallback otomatis.
Alur: coba model 1 → gagal → coba model 2 → gagal → raise error
"""

import httpx
from config.settings import settings
from config.models import AI_MODELS, DEFAULT_SYSTEM_PROMPT, AIModel
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AIError(Exception):
    """Error umum dari AI client."""

class AIAllModelsFailedError(AIError):
    """Semua model dalam fallback chain gagal."""


class OpenRouterClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "X-Title": "Telegram AI Bot",
            },
            timeout=settings.request_timeout,
        )

    async def chat(self, messages, system_prompt=DEFAULT_SYSTEM_PROMPT,
                   model_override=None, role=None) -> tuple[str, str]:
        """Kirim pesan ke AI. Returns: (teks_respons, model_id_yang_dipakai)"""
        role_order = {
            "fast":     ["fast", "balanced", "smart"],
            "balanced": ["balanced", "fast", "smart"],
            "smart":    ["smart", "balanced", "fast"],
        }
        if model_override:
            models_to_try = [model_override]
        elif role and role in role_order:
            order = role_order[role]
            models_to_try = [m for r in order for m in AI_MODELS if m.role == r]
        else:
            models_to_try = AI_MODELS

        full_messages = [{"role": "system", "content": system_prompt}] + messages
        last_error = None

        for model in models_to_try:
            try:
                logger.info("trying_model", model=model.display_name)
                text = await self._request(full_messages, model)
                logger.info("model_success", model=model.display_name)
                return text, model.model_id
            except Exception as e:
                last_error = e
                logger.warning("model_failed", model=model.display_name, error=str(e))
                continue  # coba model berikutnya

        raise AIAllModelsFailedError(f"Semua model gagal: {last_error}") from last_error

    async def _request(self, messages, model) -> str:
        """Satu request ke OpenRouter. Raise exception jika gagal."""
        payload = {
            "model": model.model_id,
            "messages": messages,
            "max_tokens": model.max_tokens,
            **model.extra_params,
        }
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices")
        if not choices:
            raise AIError(f"Response tidak valid: {data}")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise AIError(f"Respons kosong dari {model.display_name}")
        return content.strip()

# Singleton — import ai_client di mana saja
ai_client = OpenRouterClient()