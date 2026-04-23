"""
Módulo de acesso ao banco de dados MySQL.

Fornece um context manager seguro para conexões e helpers de query comuns.
"""

from contextlib import contextmanager
import logging
import os

import pymysql
import pymysql.cursors

logger = logging.getLogger("api_admissao.db")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "newdb"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 10,
}


@contextmanager
def get_db():
    """
    Context manager que garante fechamento da conexão e do cursor mesmo em caso de exceção.

    Uso:
        with get_db() as cursor:
            cursor.execute("SELECT ...")
            rows = cursor.fetchall()
    """
    connection = pymysql.connect(**DB_CONFIG)
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def buscar_ids_banco(cod_requisicao: str) -> dict:
    """
    Busca somente o IdLocalOrigem do banco de dados MySQL.

    Returns:
        dict com IdLocalOrigem (e campos nulos para compatibilidade).
    """
    empty = {"IdConvenio": None, "IdFontePagadora": None, "IdLocalOrigem": None}
    try:
        with get_db() as cursor:
            cursor.execute(
                "SELECT IdLocalOrigem FROM newdb.requisicao WHERE CodRequisicao = %s LIMIT 1",
                (cod_requisicao,),
            )
            row = cursor.fetchone()

        if not row:
            logger.warning("[DB] Requisição %s não encontrada no banco", cod_requisicao)
            return empty

        id_local = row.get("IdLocalOrigem")
        if not id_local:
            logger.warning("[DB] IdLocalOrigem vazio para %s", cod_requisicao)

        logger.info("[DB] %s → IdLocalOrigem=%s", cod_requisicao, id_local)
        return {"IdConvenio": None, "IdFontePagadora": None, "IdLocalOrigem": id_local}

    except Exception as exc:
        logger.error("[DB] Erro ao buscar IDs para %s: %s", cod_requisicao, exc)
        return empty


def inferir_id_local_origem_por_historico(
    id_fonte_pagadora=None, id_convenio=None
) -> int | None:
    """
    Infere o local de origem mais provável a partir do histórico real já salvo.
    """
    if not id_fonte_pagadora and not id_convenio:
        return None

    filtros = ["r.IdLocalOrigem IS NOT NULL", "r.IdLocalOrigem > 0"]
    params: list = []

    if id_fonte_pagadora:
        filtros.append("r.IdFontePagadora = %s")
        params.append(int(id_fonte_pagadora))
    if id_convenio:
        filtros.append("r.IdConvenio = %s")
        params.append(int(id_convenio))

    query = f"""
        SELECT
            r.IdLocalOrigem AS id,
            fi.NomFantasia   AS nome,
            COUNT(*)         AS total,
            MAX(r.IdRequisicao) AS ultimo_id
        FROM newdb.requisicao r
        LEFT JOIN newdb.fatinstituicao fi ON fi.IdInstituicao = r.IdLocalOrigem
        WHERE {' AND '.join(filtros)}
        GROUP BY r.IdLocalOrigem, fi.NomFantasia
        ORDER BY total DESC, ultimo_id DESC
        LIMIT 1
    """

    try:
        with get_db() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

            if not row and id_fonte_pagadora:
                cursor.execute(
                    "SELECT IdInstituicao AS id, NomFantasia AS nome"
                    " FROM newdb.fatinstituicao WHERE IdInstituicao = %s LIMIT 1",
                    (int(id_fonte_pagadora),),
                )
                row = cursor.fetchone()

        if row and row.get("id"):
            logger.info(
                "[LocalOrigem] fonte=%s convenio=%s → local=%s (%s)",
                id_fonte_pagadora, id_convenio, row["id"], row.get("nome"),
            )
            return int(row["id"])

    except Exception as exc:
        logger.warning("[LocalOrigem] Falha ao inferir por histórico: %s", exc)

    return None


def buscar_id_convenio_por_nome_banco(nome_convenio: str) -> int | None:
    """Busca IdConvenio direto no banco por nome (fallback quando o CSV não encontra)."""
    if not nome_convenio or not nome_convenio.strip():
        return None

    nome = nome_convenio.strip()
    nome_reduzido = nome.split("-")[0].split("/")[0].split("(")[0].strip()

    try:
        with get_db() as cursor:
            # Busca exata
            cursor.execute(
                "SELECT IdConvenio AS id FROM newdb.fatconvenio"
                " WHERE Inativo = 0 AND UPPER(TRIM(NomConvenio)) = UPPER(TRIM(%s)) LIMIT 1",
                (nome,),
            )
            row = cursor.fetchone()

            if not row:
                cursor.execute(
                    "SELECT IdConvenio AS id FROM newdb.fatconvenio"
                    " WHERE Inativo = 0 AND UPPER(NomConvenio) LIKE UPPER(%s)"
                    " ORDER BY NomConvenio ASC LIMIT 1",
                    (f"%{nome}%",),
                )
                row = cursor.fetchone()

            if not row and nome_reduzido and nome_reduzido.lower() != nome.lower():
                cursor.execute(
                    "SELECT IdConvenio AS id FROM newdb.fatconvenio"
                    " WHERE Inativo = 0 AND UPPER(NomConvenio) LIKE UPPER(%s)"
                    " ORDER BY CASE WHEN UPPER(TRIM(NomConvenio)) = UPPER(TRIM(%s)) THEN 0 ELSE 1 END,"
                    " NomConvenio ASC LIMIT 1",
                    (f"%{nome_reduzido}%", nome_reduzido),
                )
                row = cursor.fetchone()

        if row and row.get("id"):
            logger.info("[DB] Convênio '%s' → ID %s", nome_convenio, row["id"])
            return int(row["id"])

    except Exception as exc:
        logger.error("[DB] Erro ao buscar convênio '%s': %s", nome_convenio, exc)

    return None


def buscar_id_fonte_pagadora_por_nome_banco(nome_fonte: str) -> int | None:
    """Busca IdInstituicao (FontePagadora=1) diretamente no banco por nome."""
    if not nome_fonte or not nome_fonte.strip():
        return None

    nome = nome_fonte.strip()

    try:
        with get_db() as cursor:
            cursor.execute(
                "SELECT IdInstituicao AS id FROM newdb.fatinstituicao"
                " WHERE FontePagadora = 1 AND Inativo = 0"
                " AND UPPER(TRIM(NomFantasia)) = UPPER(TRIM(%s)) LIMIT 1",
                (nome,),
            )
            row = cursor.fetchone()

            if not row:
                cursor.execute(
                    "SELECT IdInstituicao AS id FROM newdb.fatinstituicao"
                    " WHERE FontePagadora = 1 AND Inativo = 0"
                    " AND UPPER(NomFantasia) LIKE UPPER(%s) LIMIT 1",
                    (f"%{nome}%",),
                )
                row = cursor.fetchone()

        if row and row.get("id"):
            logger.info("[DB] Fonte pagadora '%s' → ID %s", nome_fonte, row["id"])
            return int(row["id"])

    except Exception as exc:
        logger.error("[DB] Erro ao buscar fonte pagadora '%s': %s", nome_fonte, exc)

    return None
