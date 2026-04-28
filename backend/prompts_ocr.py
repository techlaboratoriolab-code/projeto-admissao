"""Prompts para OCR com Vertex AI."""

from pathlib import Path


_PROMPT_PATH = Path(__file__).with_name("prompts_ocr.md")


def gerar_prompt_ocr(imagem_nome: str) -> str:
    """Carrega o template de prompt OCR e injeta o nome da imagem."""
    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    return prompt_template.replace("{imagem_nome}", imagem_nome)