"""
Cliente para a API apLIS.

Encapsula autenticação, retry com backoff e parsing de respostas.
"""

import json
import logging
import os
import time

import requests

logger = logging.getLogger("api_admissao.aplis")

APLIS_URL = os.getenv("APLIS_BASE_URL", "https://lab.aplis.inf.br/api/integracao.php")
APLIS_USERNAME = os.getenv("APLIS_USUARIO", "api.lab")
APLIS_PASSWORD = os.getenv("APLIS_SENHA", "")
_HEADERS = {"Content-Type": "application/json"}

_MAX_TENTATIVAS = 6
_RETRY_STATUS = {429, 502, 503, 504}


def fazer_requisicao_aplis(
    cmd: str,
    dat: dict,
    aplis_usuario: str | None = None,
    aplis_senha: str | None = None,
) -> dict:
    """
    Faz uma requisição ao apLIS com retry e backoff exponencial.

    Args:
        cmd: Comando apLIS (ex: "admissaoSalvar", "requisicaoListar").
        dat: Dados do campo "dat" do payload.
        aplis_usuario: Sobrescreve o usuário padrão do .env.
        aplis_senha: Sobrescreve a senha padrão do .env.

    Returns:
        dict com a resposta JSON do apLIS, ou dict de erro padronizado.
    """
    usuario = aplis_usuario or APLIS_USERNAME
    senha = aplis_senha or APLIS_PASSWORD

    payload = {"ver": 1, "cmd": cmd, "dat": dat}
    body = json.dumps(payload)

    logger.info("[apLIS] → %s | usuario=%s", cmd, usuario)

    ultimo_status: int | None = None
    ultimo_texto = ""

    for tentativa in range(1, _MAX_TENTATIVAS + 1):
        try:
            resp = requests.post(
                APLIS_URL,
                auth=(usuario, senha),
                headers=_HEADERS,
                data=body,
                timeout=45,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("[apLIS] Erro de rede em %s: %s", cmd, exc)
            return {"erro": str(exc), "sucesso": 0, "dat": {}}

        ultimo_status = resp.status_code
        ultimo_texto = (resp.text or "").strip()

        logger.debug("[apLIS] %s tentativa=%d status=%d", cmd, tentativa, ultimo_status)

        # Retry em erros temporários
        if ultimo_status in _RETRY_STATUS and tentativa < _MAX_TENTATIVAS:
            espera = min(30, 2 ** tentativa)
            logger.warning("[apLIS] HTTP %d em %s — retry em %ds", ultimo_status, cmd, espera)
            time.sleep(espera)
            continue

        # Tentar parsear JSON
        try:
            data = resp.json()
        except ValueError:
            # Verificar se parece rate-limit mesmo sem JSON
            txt_upper = ultimo_texto.upper()
            if ("429" in txt_upper or "TOO MANY REQUESTS" in txt_upper) and tentativa < _MAX_TENTATIVAS:
                espera = min(30, 2 ** tentativa)
                logger.warning("[apLIS] Resposta não-JSON com rate-limit em %s — retry em %ds", cmd, espera)
                time.sleep(espera)
                continue

            logger.error("[apLIS] Resposta não-JSON em %s: %s", cmd, ultimo_texto[:200])
            return {
                "erro": "Resposta inválida do apLIS",
                "texto": ultimo_texto,
                "status_code": ultimo_status,
                "sucesso": 0,
                "dat": {},
            }

        sucesso = data.get("dat", {}).get("sucesso")
        if sucesso == 1:
            logger.info("[apLIS] ✓ %s OK", cmd)
        else:
            logger.warning("[apLIS] %s retornou sucesso=%s", cmd, sucesso)

        return data

    return {
        "erro": f"Falha após {_MAX_TENTATIVAS} tentativas",
        "status_code": ultimo_status,
        "texto": ultimo_texto,
        "sucesso": 0,
        "dat": {},
    }


def salvar_admissao_aplis(
    dados_admissao: dict,
    aplis_usuario: str | None = None,
    aplis_senha: str | None = None,
) -> dict:
    """Atalho para o comando admissaoSalvar."""
    return fazer_requisicao_aplis("admissaoSalvar", dados_admissao, aplis_usuario, aplis_senha)
