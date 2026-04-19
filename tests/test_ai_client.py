import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ai.client import OpenRouterClient, AIAllModelsFailedError


@pytest.mark.asyncio
async def test_chat_success_first_model():
    """Model pertama berhasil → langsung return, tidak coba model lain."""
    client = OpenRouterClient()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Halo!"}}]
    }
    with patch.object(client._client, "post", new_callable=AsyncMock) as mock:
        mock.return_value = mock_resp
        result, model_id = await client.chat([{"role": "user", "content": "Halo"}])
    assert result == "Halo!"
    assert mock.call_count == 1  # hanya 1 model yang dicoba


@pytest.mark.asyncio
async def test_chat_fallback_to_second_model():
    """Model pertama gagal → otomatis fallback ke model kedua."""
    client = OpenRouterClient()
    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count; call_count += 1
        if call_count == 1: raise Exception("Model 1 timeout")
        resp = MagicMock(); resp.raise_for_status = MagicMock()
        resp.json.return_value = {"choices": [{"message": {"content": "Dari model 2"}}]}
        return resp

    with patch.object(client._client, "post", side_effect=mock_post):
        result, _ = await client.chat([{"role": "user", "content": "Test"}])
    assert result == "Dari model 2"
    assert call_count == 2


@pytest.mark.asyncio
async def test_all_models_fail_raises_error():
    """Semua model gagal → harus raise AIAllModelsFailedError."""
    client = OpenRouterClient()
    with patch.object(
        client._client, "post", new_callable=AsyncMock,
        side_effect=Exception("semua error")
    ):
        with pytest.raises(AIAllModelsFailedError):
            await client.chat([{"role": "user", "content": "Test"}])