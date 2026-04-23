"""
Cache em memória para médicos, convênios e instituições (carregados de CSVs).
"""

import csv
import logging
import os
import re

logger = logging.getLogger("api_admissao.cache")

# ---------------------------------------------------------------------------
# Dicionários globais
# ---------------------------------------------------------------------------
MEDICOS_CACHE: dict = {}       # {"CRM_UF": {id, nome, crm, uf}}
CONVENIOS_CACHE: dict = {}     # {"IdConvenio": {id, nome}}
INSTITUICOES_CACHE: dict = {}  # {"IdInstituicao": {id, nome}}

_DADOS_DIR = os.path.join(os.path.dirname(__file__), "..", "dados")


# ---------------------------------------------------------------------------
# Carregamento dos CSVs
# ---------------------------------------------------------------------------

def carregar_medicos_csv() -> None:
    """Carrega médicos do CSV mais recente para o cache."""
    global MEDICOS_CACHE

    csv_path = os.path.join(_DADOS_DIR, "medicos_extraidos_20260120_155027.csv")
    if not os.path.exists(csv_path):
        logger.warning("[CSV] Arquivo de médicos não encontrado: %s", csv_path)
        return

    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                chave = f"{row['CRM']}_{row['CRMUF']}"
                MEDICOS_CACHE[chave] = {
                    "id": row["CodMedico"],
                    "nome": row["NomMedico"],
                    "crm": row["CRM"],
                    "uf": row["CRMUF"],
                }
        logger.info("[CSV] %d médicos carregados", len(MEDICOS_CACHE))
    except Exception as exc:
        logger.error("[CSV] Erro ao carregar médicos: %s", exc)


def carregar_convenios_csv() -> None:
    """Carrega convênios do CSV para o cache."""
    global CONVENIOS_CACHE

    csv_path = os.path.join(_DADOS_DIR, "convenios_extraidos_20260120_155027.csv")
    if not os.path.exists(csv_path):
        logger.warning("[CSV] Arquivo de convênios não encontrado: %s", csv_path)
        return

    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                CONVENIOS_CACHE[row["IdConvenio"]] = {
                    "id": row["IdConvenio"],
                    "nome": row["NomConvenio"],
                }
        logger.info("[CSV] %d convênios carregados", len(CONVENIOS_CACHE))
    except Exception as exc:
        logger.error("[CSV] Erro ao carregar convênios: %s", exc)


def carregar_instituicoes_csv() -> None:
    """Carrega instituições do CSV mais recente para o cache."""
    global INSTITUICOES_CACHE
    INSTITUICOES_CACHE = {}

    if not os.path.exists(_DADOS_DIR):
        logger.warning("[CSV] Pasta de dados não encontrada: %s", _DADOS_DIR)
        return

    arquivos = [
        os.path.join(_DADOS_DIR, f)
        for f in os.listdir(_DADOS_DIR)
        if f.endswith(".csv") and (
            f.startswith("instituicoes_extraidas_") or f.startswith("locais_origem_extraidos_")
        )
    ]

    if not arquivos:
        logger.warning("[CSV] Nenhum CSV de instituições em %s", _DADOS_DIR)
        return

    csv_path = sorted(arquivos)[-1]
    logger.info("[CSV] Carregando instituições de: %s", os.path.basename(csv_path))

    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                INSTITUICOES_CACHE[row["IdInstituicao"]] = {
                    "id": row["IdInstituicao"],
                    "nome": row["NomFantasia"],
                }
        logger.info("[CSV] %d instituições carregadas", len(INSTITUICOES_CACHE))
    except Exception as exc:
        logger.error("[CSV] Erro ao carregar instituições: %s", exc)


def atualizar_cache_local_origem_do_banco() -> bool:
    """Atualiza o cache de local de origem a partir do banco (para uso no scheduler)."""
    try:
        from extrair_locais_origem import extrair_locais_origem  # noqa: PLC0415

        arquivo = extrair_locais_origem()
        carregar_instituicoes_csv()
        logger.info("[LocalOrigem] Cache atualizado. Arquivo: %s", arquivo)
        return True
    except Exception as exc:
        logger.error("[LocalOrigem] Erro ao atualizar cache: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Lookups por ID
# ---------------------------------------------------------------------------

def buscar_medico_por_crm(crm: str, uf: str) -> dict | None:
    return MEDICOS_CACHE.get(f"{crm}_{uf}")


def buscar_convenio_por_id(id_convenio) -> dict | None:
    return CONVENIOS_CACHE.get(str(id_convenio))


def buscar_instituicao_por_id(id_instituicao) -> dict | None:
    return INSTITUICOES_CACHE.get(str(id_instituicao))


# ---------------------------------------------------------------------------
# Lookups por nome
# ---------------------------------------------------------------------------

_STOPWORDS = {"DE", "DA", "DO", "DOS", "DAS", "E", "EM"}


def buscar_instituicao_por_nome(nome_busca: str) -> dict | None:
    """
    Busca instituição no cache por nome com três estratégias:
    1. Exata  2. Palavra-chave inicial  3. Parcial (contém)
    """
    if not nome_busca or not isinstance(nome_busca, str):
        return None

    alvo = nome_busca.upper().strip()

    # 1. Exata
    for dados in INSTITUICOES_CACHE.values():
        if dados.get("nome", "").upper() == alvo:
            return dados

    # 2. Palavra-chave
    palavra_chave = next(
        (p.strip(",-()[]") for p in alvo.split() if len(p.strip(",-()[]")) >= 3 and p.strip(",-()[]") not in _STOPWORDS),
        None,
    )
    if palavra_chave:
        for dados in INSTITUICOES_CACHE.values():
            if dados.get("nome", "").upper().startswith(palavra_chave):
                return dados

    # 3. Parcial
    for dados in INSTITUICOES_CACHE.values():
        nome = dados.get("nome", "").upper()
        if alvo in nome or nome in alvo:
            return dados

    logger.warning("[Cache] Instituição '%s' não encontrada", nome_busca)
    return None


def buscar_convenio_por_nome(nome_busca: str) -> dict | None:
    """Busca convênio no cache por nome."""
    if not nome_busca:
        return None

    alvo = nome_busca.upper().strip()
    alvo_limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", alvo)).strip()

    for dados in CONVENIOS_CACHE.values():
        nome = dados.get("nome", "").upper()
        if nome == alvo:
            return dados
        nome_limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", nome)).strip()
        if nome_limpo == alvo_limpo:
            return dados

    return None


# ---------------------------------------------------------------------------
# Lookup reverso por nome → ID
# ---------------------------------------------------------------------------

def buscar_id_convenio_por_nome(nome_convenio: str):
    """Busca ID do convênio pelo nome (busca no cache, fallback no banco)."""
    from db import buscar_id_convenio_por_nome_banco  # lazy import para evitar circular

    if not nome_convenio:
        return None

    alvo = nome_convenio.strip().upper()
    alvo_limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", alvo)).strip()

    for id_conv, dados in CONVENIOS_CACHE.items():
        nome = dados.get("nome", "").strip().upper()
        if nome == alvo:
            return id_conv
        nome_limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", nome)).strip()
        if nome_limpo == alvo_limpo:
            return id_conv

    return buscar_id_convenio_por_nome_banco(nome_convenio)


def buscar_id_instituicao_por_nome(nome_instituicao: str):
    """Busca ID da instituição pelo nome (busca no cache, fallback no banco)."""
    from db import buscar_id_fonte_pagadora_por_nome_banco  # lazy import

    if not nome_instituicao:
        return None

    alvo = nome_instituicao.strip().upper()
    alvo_limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", alvo)).strip()

    for id_inst, dados in INSTITUICOES_CACHE.items():
        nome = dados.get("nome", "").strip().upper()
        if nome == alvo:
            return id_inst
        nome_limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", nome)).strip()
        if nome_limpo == alvo_limpo:
            return id_inst

    return buscar_id_fonte_pagadora_por_nome_banco(nome_instituicao)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def obter_id_convenio_default() -> int | None:
    """Retorna um ID de convênio válido para usar como padrão (prioriza PARTICULAR)."""
    if CONVENIOS_CACHE:
        for id_conv, dados in CONVENIOS_CACHE.items():
            nome = dados.get("nome", "").upper()
            if any(k in nome for k in ("PARTICULAR", "PRIVADO", "SEM CONVENIO")):
                return int(id_conv)
        return int(list(CONVENIOS_CACHE.keys())[0])

    # Fallback: consulta direto no banco
    from db import get_db  # lazy import

    try:
        with get_db() as cursor:
            for q in (
                "SELECT IdConvenio AS id FROM newdb.fatconvenio WHERE Inativo=0 AND UPPER(NomConvenio) LIKE '%ARTICULAR%' LIMIT 1",
                "SELECT IdConvenio AS id FROM newdb.fatconvenio WHERE Inativo=0 LIMIT 1",
                "SELECT IdConvenio AS id FROM newdb.fatconvenio LIMIT 1",
            ):
                cursor.execute(q)
                row = cursor.fetchone()
                if row:
                    return int(row["id"])
    except Exception as exc:
        logger.error("[Default] Erro ao buscar convênio default: %s", exc)

    return None


def obter_id_instituicao_default() -> int | None:
    """Retorna um ID de instituição válido para usar como padrão."""
    if INSTITUICOES_CACHE:
        return int(list(INSTITUICOES_CACHE.keys())[0])

    from db import get_db  # lazy import

    try:
        with get_db() as cursor:
            for q in (
                "SELECT IdInstituicao AS id FROM newdb.fatinstituicao WHERE FontePagadora=1 AND Inativo=0 AND UPPER(NomFantasia) LIKE '%ARTICULAR%' LIMIT 1",
                "SELECT IdInstituicao AS id FROM newdb.fatinstituicao WHERE FontePagadora=1 AND Inativo=0 LIMIT 1",
                "SELECT IdInstituicao AS id FROM newdb.fatinstituicao WHERE Inativo=0 LIMIT 1",
                "SELECT IdInstituicao AS id FROM newdb.fatinstituicao LIMIT 1",
            ):
                cursor.execute(q)
                row = cursor.fetchone()
                if row:
                    return int(row["id"])
    except Exception as exc:
        logger.error("[Default] Erro ao buscar instituição default: %s", exc)

    return None


def obter_id_medico_default() -> int | None:
    """Retorna o ID do primeiro médico disponível no cache."""
    if not MEDICOS_CACHE:
        return None
    return int(list(MEDICOS_CACHE.values())[0]["id"])


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

def inicializar_caches() -> None:
    """Carrega todos os caches na inicialização da aplicação."""
    logger.info("[Cache] Inicializando caches de CSV...")
    carregar_medicos_csv()
    carregar_convenios_csv()
    carregar_instituicoes_csv()
    logger.info("[Cache] Caches prontos: médicos=%d, convênios=%d, instituições=%d",
                len(MEDICOS_CACHE), len(CONVENIOS_CACHE), len(INSTITUICOES_CACHE))
