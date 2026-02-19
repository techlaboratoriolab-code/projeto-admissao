# -*- coding: utf-8 -*-
"""
Endpoints para dropdowns da tela de admissão
"""
from flask import Blueprint, jsonify

dropdowns_bp = Blueprint('dropdowns', __name__)

# Estas variáveis serão injetadas após criar o blueprint
_logger = None
_instituicoes_cache = None
_pymysql = None
_db_config = None

def init_dropdowns(logger, instituicoes_cache, pymysql, db_config):
    """Inicializa as dependências do blueprint"""
    global _logger, _instituicoes_cache, _pymysql, _db_config
    _logger = logger
    _instituicoes_cache = instituicoes_cache
    _pymysql = pymysql
    _db_config = db_config

@dropdowns_bp.route('/api/locais-origem', methods=['GET'])
def listar_locais_origem():
    """
    Lista locais de origem: clinicas/hospitais que ENVIAM o exame.
    Sao diferentes dos convenios (planos de saude).
    Fonte: fatinstituicao WHERE Local = 1 AND Inativo = 0.
    """
    try:
        connection = _pymysql.connect(**_db_config)
        cursor = connection.cursor(_pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT
                IdInstituicao AS id,
                NomFantasia   AS nome
            FROM newdb.fatinstituicao
            WHERE Local = 1
              AND Inativo = 0
              AND NomFantasia IS NOT NULL
              AND NomFantasia != ''
            ORDER BY NomFantasia ASC
        """)
        locais = cursor.fetchall()
        cursor.close()
        connection.close()

        return jsonify({
            "sucesso": 1,
            "total": len(locais),
            "locais": locais
        }), 200
    except Exception as e:
        _logger.error(f"[API] Erro ao listar locais de origem: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@dropdowns_bp.route('/api/fontes-pagadoras', methods=['GET'])
def listar_fontes_pagadoras():
    """
    Lista fontes pagadoras: entidades que PAGAM pelos exames.
    Fonte: fatinstituicao WHERE FontePagadora = 1 AND Inativo = 0.
    Diferente de convenios (fatconvenio) e de locais de origem (Local=1).
    """
    try:
        connection = _pymysql.connect(**_db_config)
        cursor = connection.cursor(_pymysql.cursors.DictCursor)

        query = """
            SELECT
                IdInstituicao AS id,
                NomFantasia   AS nome
            FROM newdb.fatinstituicao
            WHERE FontePagadora = 1
              AND Inativo = 0
              AND NomFantasia IS NOT NULL
              AND NomFantasia != ''
            ORDER BY NomFantasia ASC
        """
        cursor.execute(query)
        fontes = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "sucesso": 1,
            "total": len(fontes),
            "fontes": fontes
        }), 200
    except Exception as e:
        _logger.error(f"[API] Erro ao listar fontes pagadoras: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500
