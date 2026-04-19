"""
Daftar model AI dan urutan fallback-nya.
Untuk ganti model → edit file ini saja, tidak perlu menyentuh logika lain.
"""

from dataclasses import dataclass, field


@dataclass
class AIModel:
    """Representasi satu model AI."""
    model_id: str       # ID resmi di OpenRouter
    display_name: str   # Nama tampilan untuk log/debug
    provider: str       # Nama provider
    is_free: bool = True
    max_tokens: int = 2048
    role: str="balaced"
    extra_params: dict = field(default_factory=dict)


# ================================================
# DAFTAR MODEL — Urutan = prioritas fallback
# Model pertama = utama, berikutnya = cadangan
# ================================================
AI_MODELS: list[AIModel] = [
    # ⚡ FAST (respon cepat)
    AIModel(
        model_id="arcee-ai/trinity-large-preview:free",
        display_name="Trinity Large",
        provider="Arcee Ai",
        role="fast",
        max_tokens=4096,
    ),

    # ⚖️ BALANCE (utama)
    AIModel(
        model_id="openai/gpt-oss-120b:free",
        display_name="GPT oss",
        provider="Open Ai",
        role="balanced",
        max_tokens=8192,
    ),

    # 🧠 SMART (reasoning berat)
    AIModel(
        model_id="nvidia/nemotron-3-super-120b-a12b:free",
        display_name="Nemotron 3 Super",
        provider="NVIDIA",
        role="smart",
        max_tokens=8192,
    ),
]

# System prompt default — bisa di-override per user/grup
DEFAULT_SYSTEM_PROMPT = """Kamu adalah asisten AI yang membantu, ramah, dan cerdas.
Jawab dalam bahasa yang sama dengan pertanyaan user.
Berikan jawaban yang jelas, terstruktur, dan bermanfaat."""