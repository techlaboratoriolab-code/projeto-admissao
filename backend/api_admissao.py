"""
API Backend para Sistema de AdmissÃ£o
Conecta interface React com apLIS
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv
import boto3
import tempfile
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import logging
from logging.handlers import RotatingFileHandler
import time
from collections import deque
import csv
import pymysql
from dateutil.relativedelta import relativedelta

# Importar prompts de OCR (arquivo separado para organizaÃ§Ã£o)
from prompts_ocr import gerar_prompt_ocr

# Carregar variÃ¡veis de ambiente do arquivo .env na pasta backend
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ============================================
# IMPORTAR CLIENTE SUPABASE (HISTÃ“RICO)
# ============================================
try:
    from supabase_client import supabase_manager
    SUPABASE_ENABLED = supabase_manager.is_connected()
except ImportError as e:
    print(f"âš ï¸ MÃ³dulo supabase_client nÃ£o encontrado: {e}")
    print("âš ï¸ Execute: pip install supabase")
    SUPABASE_ENABLED = False
    supabase_manager = None

# Configurar encoding UTF-8 para o console do Windows (evita erros com emojis)
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# ========================================
# CONFIGURAÃ‡ÃƒO DE LOGGING
# ========================================
# Criar diretÃ³rio de logs se nÃ£o existir
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Logger principal
logger = logging.getLogger('api_admissao')
logger.setLevel(logging.DEBUG)

# Handler para arquivo (rotaÃ§Ã£o automÃ¡tica)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'api_admissao.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Handler para console (colorido)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Configurar Vertex AI
GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID', 'spry-catcher-449921-h8')
GOOGLE_LOCATION = os.getenv('GOOGLE_LOCATION', 'us-central1')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS',
                                      r'C:\Users\Windows 11\Downloads\spry-catcher-449921-h8-bbc989e73ec4 (1).json')

# Inicializar Vertex AI
vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)

# ConfiguraÃ§Ãµes da API de CPF (Receita Federal)
CPF_API_BASE_URL = "https://ws.hubdodesenvolvedor.com.br/v2/cpf/"
CPF_API_TOKEN = os.getenv('CPF_API_TOKEN', '')

# ========================================
# CONFIGURAÃ‡Ã•ES DO BANCO DE DADOS MYSQL
# ========================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'newdb'),
    'charset': 'utf8mb4'
}

def buscar_ids_banco(cod_requisicao):
    """
    Busca IdConvenio, IdFontePagadora e IdLocalOrigem direto do banco de dados MySQL

    Args:
        cod_requisicao: CÃ³digo da requisiÃ§Ã£o (ex: '0040000356004')

    Returns:
        dict: {'IdConvenio': int, 'IdFontePagadora': int, 'IdLocalOrigem': int} ou None para cada campo
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT IdConvenio, IdFontePagadora, IdLocalOrigem
            FROM newdb.requisicao
            WHERE CodRequisicao = %s
            LIMIT 1
        """

        cursor.execute(query, (cod_requisicao,))
        resultado = cursor.fetchone()

        cursor.close()
        connection.close()

        if resultado:
            logger.info(f"[DB] âœ… RequisiÃ§Ã£o {cod_requisicao} encontrada no banco!")
            logger.info(f"[DB]   - IdConvenio: {resultado.get('IdConvenio')} {'âœ…' if resultado.get('IdConvenio') else 'âš ï¸ (None/vazio)'}")
            logger.info(f"[DB]   - IdFontePagadora: {resultado.get('IdFontePagadora')} {'âœ…' if resultado.get('IdFontePagadora') else 'âš ï¸ (None/vazio)'}")
            logger.info(f"[DB]   - IdLocalOrigem: {resultado.get('IdLocalOrigem')} {'âœ…' if resultado.get('IdLocalOrigem') else 'âš ï¸ (None/vazio)'}")
            
            # Avisos especÃ­ficos para IDs que sÃ£o None
            if not resultado.get('IdConvenio'):
                logger.warning(f"[DB] âš ï¸ IdConvenio estÃ¡ None! ConvÃªnio nÃ£o foi salvo ao criar a requisiÃ§Ã£o")
            if not resultado.get('IdFontePagadora'):
                logger.warning(f"[DB] âš ï¸ IdFontePagadora estÃ¡ None! Fonte pagadora nÃ£o foi salva ao criar a requisiÃ§Ã£o")
            if not resultado.get('IdLocalOrigem'):
                logger.warning(f"[DB] âš ï¸ IdLocalOrigem estÃ¡ None! Local de origem nÃ£o foi salvo ao criar a requisiÃ§Ã£o")
            
            return resultado
        else:
            logger.warning(f"[DB] âŒ RequisiÃ§Ã£o {cod_requisicao} NÃƒO encontrada no banco")
            logger.warning(f"[DB] ðŸ’¡ Verifique se o cÃ³digo da requisiÃ§Ã£o estÃ¡ correto")
            return {'IdConvenio': None, 'IdFontePagadora': None, 'IdLocalOrigem': None}

    except Exception as e:
        logger.error(f"[DB] Erro ao buscar IDs do banco para {cod_requisicao}: {e}")
        return {'IdConvenio': None, 'IdFontePagadora': None, 'IdLocalOrigem': None}

def buscar_dados_paciente_via_api(cod_requisicao):
    """
    Busca dados do paciente atravÃ©s do requisicaoResultado da API
    E faz lookup reverso para encontrar os IDs de ConvÃªnio, Fonte Pagadora e Local de Origem
    
    Args:
        cod_requisicao: CÃ³digo da requisiÃ§Ã£o
        
    Returns:
        dict com dados do paciente da API (incluindo IDs) ou None
    """
    try:
        logger.info(f"[API] Buscando dados do paciente via requisicaoResultado: {cod_requisicao}")
        
        dat_resultado = {"codRequisicao": cod_requisicao}
        resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

        if resposta_resultado.get("dat", {}).get("sucesso") == 1:
            dados_resultado = resposta_resultado.get("dat", {})
            paciente_api = dados_resultado.get("paciente", {})
            
            if paciente_api:
                logger.info(f"[API] âœ… Dados do paciente obtidos via API")
                
                # LOOKUP REVERSO: Buscar IDs baseado nos nomes retornados pela API
                id_convenio = None
                id_local_origem = None
                id_fonte_pagadora = None
                
                # 1. Buscar ID do ConvÃªnio pelo nome
                nome_convenio = paciente_api.get("convenio")
                if nome_convenio:
                    logger.info(f"[API] Nome do convenio da API: '{nome_convenio}'")
                    id_convenio = _buscar_id_por_nome_convenio(nome_convenio)
                    if id_convenio:
                        logger.info(f"[API] OK ID do convenio encontrado: {id_convenio}")
                    else:
                        logger.warning(f"[API] AVISO ID do convenio NAO encontrado para '{nome_convenio}'")
                else:
                    logger.warning(f"[API] AVISO API nao retornou nome do convenio")
                
                # 2. Buscar ID do Local de Origem pelo nome
                local_origem = dados_resultado.get("localOrigem", {})
                nome_local = local_origem.get("nome") if isinstance(local_origem, dict) else None
                if nome_local:
                    logger.info(f"[API] Nome do local de origem da API: '{nome_local}'")
                    id_local_origem = _buscar_id_por_nome_instituicao(nome_local)
                    if id_local_origem:
                        logger.info(f"[API] OK ID do local de origem encontrado: {id_local_origem}")
                    else:
                        logger.warning(f"[API] AVISO ID do local de origem NAO encontrado para '{nome_local}'")
                else:
                    logger.warning(f"[API] AVISO API nao retornou nome do local de origem")
                
                # 3. Fonte Pagadora - API nÃ£o retorna, deixar None por enquanto
                logger.info(f"[API] INFO Fonte pagadora nao disponivel na API requisicaoResultado")
                
                # Mapear dados da API para estrutura unificada
                dados_mapeados = {
                    "origem": "API",
                    "NomPaciente": paciente_api.get("nome"),
                    "CPF": paciente_api.get("cpf"),
                    "DtaNascimento": paciente_api.get("dtaNascimento") or paciente_api.get("dtaNasc"),
                    "Sexo": paciente_api.get("sexo"),
                    "RGNumero": paciente_api.get("rg"),
                    "RGOrgao": paciente_api.get("rgOrgao"),
                    "RGUF": paciente_api.get("rgUF") or paciente_api.get("uf"),
                    "NomMae": paciente_api.get("nomeMae"),
                    "EstadoCivil": paciente_api.get("estadoCivil"),
                    "Passaporte": paciente_api.get("passaporte"),
                    "MatConvenio": paciente_api.get("matricula"),
                    "ValidadeMatricula": paciente_api.get("validadeMatricula"),
                    "Email": paciente_api.get("email"),
                    "TelCelular": paciente_api.get("telefone") or paciente_api.get("telCelular"),
                    "TelFixo": paciente_api.get("telFixo"),
                    # IDs obtidos via lookup reverso
                    "IdConvenio": id_convenio,
                    "IdLocalOrigem": id_local_origem,
                    "IdFontePagadora": id_fonte_pagadora,
                }
                
                # EndereÃ§o pode vir como objeto
                endereco_api = paciente_api.get("endereco", {})
                if isinstance(endereco_api, dict):
                    dados_mapeados.update({
                        "Cep": endereco_api.get("cep"),
                        "Logradouro": endereco_api.get("logradouro"),
                        "NumEndereco": endereco_api.get("numero") or endereco_api.get("numEndereco"),
                        "Complemento": endereco_api.get("complemento"),
                        "Bairro": endereco_api.get("bairro"),
                        "Cidade": endereco_api.get("cidade"),
                        "UF": endereco_api.get("uf"),
                    })
                else:
                    dados_mapeados.update({
                        "Cep": paciente_api.get("cep"),
                        "Logradouro": paciente_api.get("logradouro"),
                        "NumEndereco": paciente_api.get("numEndereco"),
                        "Complemento": paciente_api.get("complemento"),
                        "Bairro": paciente_api.get("bairro"),
                        "Cidade": paciente_api.get("cidade"),
                        "UF": paciente_api.get("uf"),
                    })
                
                return dados_mapeados
            else:
                logger.warning(f"[API] âš ï¸ Paciente nÃ£o encontrado no resultado da API")
                return None
        else:
            logger.warning(f"[API] âš ï¸ Falha ao buscar via requisicaoResultado")
            return None

    except Exception as e:
        logger.error(f"[API] âŒ Erro ao buscar dados via API: {e}")
        return None


def buscar_dados_completos_paciente(cod_paciente):
    """
    Busca TODOS os dados do paciente direto do banco de dados (FALLBACK)

    Args:
        cod_paciente: CÃ³digo do paciente

    Returns:
        dict com todos os dados do paciente ou None
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT
                p.CodPaciente,
                p.NomPaciente,
                p.CPF,
                p.DtaNascimento,
                p.Sexo,
                p.RGNumero,
                p.RGOrgao,
                p.RGUF,
                p.NomMae,
                p.EstadoCivil,
                p.Passaporte,
                p.MatConvenio,
                p.ValidadeMatricula,
                (SELECT ContatoEmail FROM newdb.requisicaocontato rc
                 INNER JOIN newdb.requisicao r ON rc.IdRequisicao = r.IdRequisicao
                 WHERE r.CodPaciente = p.CodPaciente AND ContatoEmail IS NOT NULL AND ContatoEmail != ''
                 ORDER BY rc.DtaContato DESC LIMIT 1) as Email,
                (SELECT NumGuiaConvenio FROM newdb.requisicao r
                 WHERE r.CodPaciente = p.CodPaciente AND NumGuiaConvenio IS NOT NULL AND NumGuiaConvenio != ''
                 ORDER BY r.DtaColeta DESC LIMIT 1) as NumGuiaConvenio
            FROM newdb.paciente p
            LEFT JOIN newdb.cep c ON p.CodCEP = c.CodCep
            LEFT JOIN newdb.telefone t1 ON p.CodPaciente = t1.CodOrigem AND t1.Origem = 1 AND t1.TipTelefone = 3
            LEFT JOIN newdb.telefone t2 ON p.CodPaciente = t2.CodOrigem AND t2.Origem = 1 AND t2.TipTelefone = 1
            WHERE p.CodPaciente = %s
            LIMIT 1
        """

        cursor.execute(query, (cod_paciente,))
        resultado = cursor.fetchone()

        cursor.close()
        connection.close()

        if resultado:
            logger.info(f"[DB] Dados completos do paciente {cod_paciente} encontrados no banco")
            resultado["origem"] = "BANCO_SQL"
            return resultado
        else:
            logger.warning(f"[DB] Paciente {cod_paciente} nÃ£o encontrado no banco")
            return None

    except Exception as e:
        logger.error(f"[DB] Erro ao buscar dados do paciente {cod_paciente}: {e}")
        return None

def buscar_requisicao_correspondente(cod_requisicao):
    """
    Busca requisiÃ§Ã£o correspondente seguindo a regra:
    - Se comeÃ§a com 0085 â†’ busca correspondente 0200
    - Se comeÃ§a com 0200 â†’ busca correspondente 085

    Retorna dados do PACIENTE da requisiÃ§Ã£o correspondente para sincronizaÃ§Ã£o

    Args:
        cod_requisicao: CÃ³digo da requisiÃ§Ã£o (ex: '0085075767003' ou '0200051495002')

    Returns:
        dict com dados do paciente da requisiÃ§Ã£o correspondente ou None
    """
    try:
        # Verificar tipo de requisiÃ§Ã£o
        if cod_requisicao.startswith('0085'):
            tipo_atual = '0085'
            tipo_correspondente = '0200'
            prefixo_busca = '0200%'
        elif cod_requisicao.startswith('0200'):
            tipo_atual = '0200'
            tipo_correspondente = '0085'
            prefixo_busca = '0085%'
        else:
            # NÃ£o Ã© uma requisiÃ§Ã£o que precisa de sincronizaÃ§Ã£o
            return None

        logger.info(f"[DB_SYNC] â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
        logger.info(f"[DB_SYNC] RequisiÃ§Ã£o {tipo_atual}: {cod_requisicao}")
        logger.info(f"[DB_SYNC] Buscando correspondente {tipo_correspondente}...")
        logger.info(f"[DB_SYNC] â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")

        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # ESTRATÃ‰GIA: Buscar requisiÃ§Ã£o correspondente do MESMO PACIENTE e MESMA DATA
        # IMPORTANTE: O sufixo NÃƒO Ã© necessariamente igual! (ex: 0085...005 vs 0200...006)
        # Por isso buscamos pelo paciente + data ao invÃ©s de sufixo exato
        # Ordenamos por proximidade do nÃºmero da requisiÃ§Ã£o para pegar a mais prÃ³xima
        query = """
            SELECT
                r2.CodRequisicao,
                r2.IdConvenio,
                r2.IdFontePagadora,
                r2.IdLocalOrigem,
                r2.CodPaciente,
                r2.NumGuiaConvenio,
                r2.DtaSolicitacao,
                p.NomPaciente,
                p.CPF,
                p.DtaNascimento as DtaNasc,
                p.Sexo,
                p.RGNumero as RG,
                p.RGOrgao,
                p.RGUF,
                p.NomMae,
                p.EstadoCivil,
                p.Passaporte,
                p.MatConvenio,
                p.ValidadeMatricula,
                c.Cep as CEP,
                c.DesEndereco as Logradouro,
                p.NumEndereco,
                p.ComEndereco as Complemento,
                c.Bairro,
                c.Cidade,
                c.Estado as UF,
                t1.NumTelefone as TelCelular,
                t2.NumTelefone as TelFixo,
                ABS(CAST(SUBSTRING(r2.CodRequisicao, 5) AS SIGNED) - CAST(SUBSTRING(r1.CodRequisicao, 5) AS SIGNED)) as distancia
            FROM newdb.requisicao r1
            INNER JOIN newdb.requisicao r2 ON r1.CodPaciente = r2.CodPaciente
                AND DATE(r1.DtaSolicitacao) = DATE(r2.DtaSolicitacao)
                AND r2.CodRequisicao LIKE %s
                AND r2.CodRequisicao != r1.CodRequisicao
            LEFT JOIN newdb.paciente p ON r2.CodPaciente = p.CodPaciente
            LEFT JOIN newdb.cep c ON p.CodCEP = c.CodCep
            LEFT JOIN newdb.telefone t1 ON p.CodPaciente = t1.CodOrigem AND t1.Origem = 1 AND t1.TipTelefone = 3
            LEFT JOIN newdb.telefone t2 ON p.CodPaciente = t2.CodOrigem AND t2.Origem = 1 AND t2.TipTelefone = 1
            WHERE r1.CodRequisicao = %s
            ORDER BY distancia ASC
            LIMIT 1
        """

        logger.info(f"[DB_SYNC] Query executada com prefixo_busca: {prefixo_busca}")
        cursor.execute(query, (prefixo_busca, cod_requisicao))
        resultado = cursor.fetchone()

        cursor.close()
        connection.close()

        if resultado:
            logger.info(f"[DB_SYNC] âœ… RequisiÃ§Ã£o correspondente encontrada!")
            logger.info(f"[DB_SYNC]    CÃ³digo: {resultado['CodRequisicao']}")
            logger.info(f"[DB_SYNC]    Paciente: {resultado.get('NomPaciente')} | CPF: {resultado.get('CPF')}")
            logger.info(f"[DB_SYNC]    NumGuiaConvenio: {resultado.get('NumGuiaConvenio')}")
            logger.info(f"[DB_SYNC]    DistÃ¢ncia numÃ©rica: {resultado.get('distancia')} (quanto menor, mais prÃ³ximas as requisiÃ§Ãµes)")
            logger.info(f"[DB_SYNC] â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
            return resultado
        else:
            logger.warning(f"[DB_SYNC] âš ï¸ Nenhuma requisiÃ§Ã£o correspondente encontrada")
            logger.info(f"[DB_SYNC] â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
            return None

    except Exception as e:
        logger.error(f"[DB_SYNC] Erro ao buscar requisiÃ§Ã£o correspondente: {e}")
        return None

def buscar_requisicao_correspondente_aplis(cod_requisicao):
    """
    Busca requisiÃ§Ã£o correspondente DIRETO DO APLIS (sem depender do banco local)

    Regra:
    - Se comeÃ§a com 0085 â†’ busca 0200 com mesmo sufixo
    - Se comeÃ§a com 0200 â†’ busca 0085 com mesmo sufixo

    Exemplo:
    - 0085075447003 â†’ 0200075447003
    - 0200051653008 â†’ 0085051653008

    Args:
        cod_requisicao: CÃ³digo da requisiÃ§Ã£o

    Returns:
        dict com dados do paciente da requisiÃ§Ã£o correspondente ou None
    """
    try:
        # Verificar tipo de requisiÃ§Ã£o
        if cod_requisicao.startswith('0085'):
            tipo_atual = '0085'
            tipo_correspondente = '0200'
            # Trocar prefixo: 0085075447003 â†’ 0200075447003
            cod_correspondente = '0200' + cod_requisicao[4:]
        elif cod_requisicao.startswith('0200'):
            tipo_atual = '0200'
            tipo_correspondente = '0085'
            # Trocar prefixo: 0200051653008 â†’ 0085051653008
            cod_correspondente = '0085' + cod_requisicao[4:]
        else:
            # NÃ£o Ã© uma requisiÃ§Ã£o que precisa de sincronizaÃ§Ã£o
            logger.info(f"[APLIS_SYNC] RequisiÃ§Ã£o {cod_requisicao} nÃ£o Ã© tipo 0085 nem 0200")
            return None

        logger.info(f"[APLIS_SYNC] RequisiÃ§Ã£o {tipo_atual}: {cod_requisicao}")
        logger.info(f"[APLIS_SYNC] Buscando correspondente {tipo_correspondente}: {cod_correspondente}")

        # Buscar no apLIS usando requisicaoListar com filtro por cÃ³digo
        # ESTRATÃ‰GIA: Buscar nos Ãºltimos 365 dias
        hoje = datetime.now()
        periodo_fim = hoje.strftime("%Y-%m-%d")
        periodo_ini = (hoje - timedelta(days=365)).strftime("%Y-%m-%d")

        dat = {
            "ordenar": "IdRequisicao",
            "idEvento": "50",
            "periodoIni": periodo_ini,
            "periodoFim": periodo_fim,
            "pagina": 1,
            "tamanho": 100  # Buscar mais para filtrar depois
        }

        resposta = fazer_requisicao_aplis("requisicaoListar", dat)

        if resposta.get("dat", {}).get("sucesso") != 1:
            logger.warning(f"[APLIS_SYNC] Erro ao buscar no apLIS: {resposta}")
            return None

        lista = resposta.get("dat", {}).get("lista", [])
        logger.info(f"[APLIS_SYNC] Encontradas {len(lista)} requisiÃ§Ãµes no perÃ­odo")

        # Procurar a requisiÃ§Ã£o correspondente na lista
        for req in lista:
            if req.get("CodRequisicao") == cod_correspondente:
                logger.info(f"[APLIS_SYNC] âœ… RequisiÃ§Ã£o correspondente encontrada: {cod_correspondente}")
                logger.info(f"[APLIS_SYNC]    Paciente: {req.get('NomPaciente')} | CPF: {req.get('CPF')}")

                # Retornar dados no mesmo formato da funÃ§Ã£o do banco
                return {
                    "CodRequisicao": req.get("CodRequisicao"),
                    "CodPaciente": req.get("CodPaciente"),
                    "NomePaciente": req.get("NomPaciente"),
                    "CPF": req.get("CPF"),
                    "DtaNasc": req.get("DtaNascimento"),  # Pode vir em formatos diferentes
                    "Sexo": req.get("Sexo"),
                    # Outros campos do apLIS (podem nÃ£o existir)
                    "IdConvenio": req.get("IdConvenio"),
                    "IdFontePagadora": req.get("IdFontePagadora"),
                    "IdLocalOrigem": req.get("IdLocalOrigem")
                }

        logger.warning(f"[APLIS_SYNC] âš ï¸ RequisiÃ§Ã£o correspondente {cod_correspondente} nÃ£o encontrada no perÃ­odo")
        return None

    except Exception as e:
        logger.error(f"[APLIS_SYNC] Erro ao buscar correspondente no apLIS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# ========================================
# FUNÃ‡ÃƒO PARA CALCULAR DATA DE NASCIMENTO A PARTIR DA IDADE
# ========================================

def calcular_data_nascimento_por_idade(idade_formatada):
    """
    Calcula a data de nascimento a partir da idade formatada.

    Args:
        idade_formatada (str): Idade no formato "48 anos", "48 anos 10 meses" ou "48 anos 10 meses 10 dias"

    Returns:
        str: Data de nascimento no formato YYYY-MM-DD ou None se nÃ£o conseguir calcular

    Exemplos:
        "48 anos" â†’ "1977-01-26" (considerando hoje como 2026-01-26)
        "48 anos 10 meses" â†’ "1977-03-26"
        "48 anos 10 meses 10 dias" â†’ "1977-03-16"
    """
    try:
        import re
        from dateutil.relativedelta import relativedelta

        if not idade_formatada or not isinstance(idade_formatada, str):
            return None

        # Extrair anos, meses e dias usando regex
        anos = 0
        meses = 0
        dias = 0

        # PadrÃ£o: "48 anos 10 meses 10 dias" ou "48 anos" ou "48 anos 10 meses"
        match_anos = re.search(r'(\d+)\s*anos?', idade_formatada, re.IGNORECASE)
        match_meses = re.search(r'(\d+)\s*meses?', idade_formatada, re.IGNORECASE)
        match_dias = re.search(r'(\d+)\s*dias?', idade_formatada, re.IGNORECASE)

        if match_anos:
            anos = int(match_anos.group(1))
        if match_meses:
            meses = int(match_meses.group(1))
        if match_dias:
            dias = int(match_dias.group(1))

        # Se nÃ£o encontrou nenhum valor, retornar None
        if anos == 0 and meses == 0 and dias == 0:
            return None

        # Calcular data de nascimento
        hoje = datetime.now()
        data_nascimento = hoje - relativedelta(years=anos, months=meses, days=dias)

        logger.info(f"[CALC_IDADE] '{idade_formatada}' â†’ Data Nascimento: {data_nascimento.strftime('%Y-%m-%d')}")
        logger.info(f"[CALC_IDADE] Detalhes: {anos} anos, {meses} meses, {dias} dias")

        return data_nascimento.strftime('%Y-%m-%d')

    except Exception as e:
        logger.error(f"[CALC_IDADE] Erro ao calcular data de nascimento de '{idade_formatada}': {e}")
        return None

# ========================================
# RATE LIMITER PARA VERTEX AI
# ========================================
class VertexAIRateLimiter:
    """
    Controla rate limiting para evitar erro 429 do Vertex AI
    Gemini tem limite de ~15 RPM (requests per minute) para flash-exp
    """
    def __init__(self, max_requests_per_minute=10, min_delay_seconds=6):
        self.max_rpm = max_requests_per_minute
        self.min_delay = min_delay_seconds
        self.request_times = deque()
        self.last_request_time = 0

    def wait_if_needed(self):
        """Aguarda se necessÃ¡rio para respeitar rate limit"""
        current_time = time.time()

        # Remover requisiÃ§Ãµes antigas (mais de 60 segundos)
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()

        # Se atingiu o limite de requisiÃ§Ãµes por minuto, aguardar
        if len(self.request_times) >= self.max_rpm:
            oldest_request = self.request_times[0]
            wait_time = 60 - (current_time - oldest_request)
            if wait_time > 0:
                logger.warning(f"[RATE LIMIT] Atingido limite de {self.max_rpm} RPM. Aguardando {wait_time:.1f}s...")
                time.sleep(wait_time)
                current_time = time.time()

        # Garantir delay mÃ­nimo entre requisiÃ§Ãµes
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            wait_time = self.min_delay - time_since_last
            logger.info(f"[RATE LIMIT] Aguardando {wait_time:.1f}s (delay mÃ­nimo entre requests)")
            time.sleep(wait_time)
            current_time = time.time()

        # Registrar esta requisiÃ§Ã£o
        self.request_times.append(current_time)
        self.last_request_time = current_time
        logger.debug(f"[RATE LIMIT] RequisiÃ§Ãµes no Ãºltimo minuto: {len(self.request_times)}/{self.max_rpm}")

# InstÃ¢ncia global do rate limiter
# ConfiguraÃ§Ã£o balanceada para evitar 429
vertex_rate_limiter = VertexAIRateLimiter(max_requests_per_minute=5, min_delay_seconds=10)

app = Flask(__name__)
# Configurar CORS para aceitar requisiÃ§Ãµes de qualquer origem (necessÃ¡rio para ngrok)
CORS(app, resources={
    r"/*": {  # Aplicar a TODAS as rotas
        "origins": "*",  # Permite qualquer origem (ngrok, localhost, etc)
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False,  # NÃ£o usar credentials com origins: "*"
        "max_age": 3600  # Cache preflight por 1 hora
    }
})

# ========================================
# REGISTRAR BLUEPRINTS
# ========================================
# Blueprint de autenticaÃ§Ã£o customizada (antiga - compatibilidade)
try:
    from api_auth import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("[OK] Blueprint de autenticaÃ§Ã£o legado registrado com sucesso!")
except ImportError as e:
    logger.warning(f"[AVISO] NÃ£o foi possÃ­vel registrar blueprint de autenticaÃ§Ã£o legado: {e}")

# Blueprint de autenticaÃ§Ã£o Supabase (nova - compartilhada com outro sistema)
try:
    from api_auth_supabase import auth_supabase_bp
    app.register_blueprint(auth_supabase_bp)
    logger.info("[OK] Blueprint de autenticaÃ§Ã£o Supabase registrado com sucesso!")
except ImportError as e:
    logger.warning(f"[AVISO] NÃ£o foi possÃ­vel registrar blueprint de autenticaÃ§Ã£o Supabase: {e}")

# ========================================
# MIDDLEWARE DE LOGGING E CORS
# ========================================
@app.before_request
def log_request_info():
    """Log de todas as requisiÃ§Ãµes recebidas + handle OPTIONS"""
    # Handle OPTIONS (CORS preflight) primeiro
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    # Log da requisiÃ§Ã£o
    logger.info("=" * 80)
    logger.info(f" REQUISIÃ‡ÃƒO RECEBIDA")
    logger.info(f"   MÃ©todo: {request.method}")
    logger.info(f"   URL: {request.url}")
    logger.info(f"   Path: {request.path}")
    logger.info(f"   Host: {request.host}")
    logger.info(f"   Remote Addr: {request.remote_addr}")
    logger.info(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    logger.info(f"   Origin: {request.headers.get('Origin', 'N/A')}")
    logger.info(f"   Referer: {request.headers.get('Referer', 'N/A')}")

    # Log do corpo da requisiÃ§Ã£o (apenas para POST/PUT)
    if request.method in ['POST', 'PUT']:
        try:
            if request.is_json:
                # Usa ensure_ascii=True para escapar emojis e caracteres Unicode
                logger.debug(f"   Body (JSON): {json.dumps(request.get_json(), indent=2, ensure_ascii=True)[:500]}")
            elif request.data:
                # Decodifica com replace para evitar erros de encoding
                logger.debug(f"   Body (raw): {request.data.decode('utf-8', errors='replace')[:500]}")
        except Exception as e:
            logger.warning(f"   Erro ao logar body: {e}")

    logger.info("=" * 80)

@app.after_request
def log_response_info(response):
    """Log de todas as respostas enviadas + garante headers CORS"""
    # Garantir headers CORS explÃ­citos em TODAS as respostas
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin, X-Requested-With'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    
    logger.info("-" * 80)
    logger.info(f" RESPOSTA ENVIADA")
    logger.info(f"   Status: {response.status_code} {response.status}")
    logger.info(f"   Content-Type: {response.content_type}")
    logger.info(f"   Content-Length: {response.content_length}")

    # Log de headers CORS importantes
    logger.debug(f"   CORS Headers:")
    logger.debug(f"      Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'N/A')}")
    logger.debug(f"      Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'N/A')}")

    logger.info("-" * 80)
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Log de erros nÃ£o tratados e retorna JSON com CORS"""
    logger.error("=" * 80)
    logger.error(f" ERRO NÃƒO TRATADO")
    logger.error(f"   Tipo: {type(e).__name__}")
    logger.error(f"   Mensagem: {str(e)}")
    logger.error(f"   Request: {request.method} {request.url}")
    logger.exception("   Stack trace:")
    logger.error("=" * 80)
    
    # Retornar resposta JSON com CORS (o @app.after_request vai adicionar os headers)
    return jsonify({
        "sucesso": 0,
        "erro": f"Erro interno do servidor: {type(e).__name__}",
        "mensagem": str(e)
    }), 500

    return jsonify({
        "erro": f"{type(e).__name__}: {str(e)}",
        "detalhes": "Erro interno do servidor - verifique os logs"
    }), 500

# DiretÃ³rio temporÃ¡rio para imagens
TEMP_IMAGES_DIR = os.path.join(tempfile.gettempdir(), 'admissao_images')
os.makedirs(TEMP_IMAGES_DIR, exist_ok=True)

# ========================================
# CACHE DE MÉDICOS, CONVÊNIOS E INSTITUIÇÕES (CSVs)
# ========================================
# Dicionários globais para busca rápida
MEDICOS_CACHE = {}  # {CRM_UF: {id, nome, crm, uf}}
CONVENIOS_CACHE = {}  # {IdConvenio: {id, nome}}
INSTITUICOES_CACHE = {}  # {IdInstituicao: {id, nome}}
LOCAIS_ORIGEM_CACHE = {}  # {IdInstituicao: {id, nome}}

def carregar_medicos_csv():
    """Carrega mÃ©dicos do CSV para cache em memÃ³ria"""
    global MEDICOS_CACHE
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'dados', 'medicos_extraidos_20260120_155027.csv')

    if not os.path.exists(csv_path):
        logger.warning(f"[CSV] Arquivo de mÃ©dicos nÃ£o encontrado: {csv_path}")
        return

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Chave: CRM + UF (ex: "28175_DF")
                chave = f"{row['CRM']}_{row['CRMUF']}"
                MEDICOS_CACHE[chave] = {
                    'id': row['CodMedico'],
                    'nome': row['NomMedico'],
                    'crm': row['CRM'],
                    'uf': row['CRMUF']
                }
        logger.info(f"[CSV] OK - {len(MEDICOS_CACHE)} mÃ©dicos carregados do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar mÃ©dicos: {e}")

def carregar_convenios_csv():
    """Carrega convÃªnios do CSV para cache em memÃ³ria"""
    global CONVENIOS_CACHE
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'dados', 'convenios_extraidos_20260120_155027.csv')

    if not os.path.exists(csv_path):
        logger.warning(f"[CSV] Arquivo de convÃªnios nÃ£o encontrado: {csv_path}")
        return

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_convenio = row['IdConvenio']
                CONVENIOS_CACHE[id_convenio] = {
                    'id': id_convenio,
                    'nome': row['NomConvenio']
                }
        logger.info(f"[CSV] OK - {len(CONVENIOS_CACHE)} convÃªnios carregados do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar convÃªnios: {e}")

def carregar_instituicoes_csv():
    """Carrega instituiÃ§Ãµes do CSV para cache em memÃ³ria"""
    global INSTITUICOES_CACHE
    
    # Buscar o arquivo CSV mais recente de instituiÃ§Ãµes
    pasta_dados = os.path.join(os.path.dirname(__file__), '..', 'dados')
    arquivos_instituicoes = []
    
    if os.path.exists(pasta_dados):
        for arquivo in os.listdir(pasta_dados):
            if arquivo.startswith('instituicoes_extraidas_') and arquivo.endswith('.csv'):
                caminho_completo = os.path.join(pasta_dados, arquivo)
                arquivos_instituicoes.append(caminho_completo)
    
    if not arquivos_instituicoes:
        logger.warning(f"[CSV] Nenhum arquivo de instituiÃ§Ãµes encontrado em {pasta_dados}")
        logger.warning(f"[CSV] Execute: python backend/extrair_instituicoes.py")
        return
    
    # Usar o arquivo mais recente (ordenar por nome, que tem timestamp)
    csv_path = sorted(arquivos_instituicoes)[-1]
    logger.info(f"[CSV] Carregando instituiÃ§Ãµes de: {os.path.basename(csv_path)}")

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_instituicao = row['IdInstituicao']
                INSTITUICOES_CACHE[id_instituicao] = {
                    'id': id_instituicao,
                    'nome': row['NomFantasia']
                }
        logger.info(f"[CSV] OK - {len(INSTITUICOES_CACHE)} instituiÃ§Ãµes carregadas do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar instituiÃ§Ãµes: {e}")

def carregar_locais_origem_csv():
    """Carrega locais de origem do CSV para cache em memória"""
    global LOCAIS_ORIGEM_CACHE
    
    # Buscar o arquivo CSV mais recente de locais de origem
    pasta_dados = os.path.join(os.path.dirname(__file__), '..', 'dados')
    arquivos_locais = []
    
    if os.path.exists(pasta_dados):
        for arquivo in os.listdir(pasta_dados):
            if arquivo.startswith('locais_origem_extraidos_') and arquivo.endswith('.csv'):
                caminho_completo = os.path.join(pasta_dados, arquivo)
                arquivos_locais.append(caminho_completo)
    
    if not arquivos_locais:
        logger.warning(f"[CSV] Nenhum arquivo de locais de origem encontrado em {pasta_dados}")
        logger.warning(f"[CSV] Execute: python backend/extrair_locais_origem.py")
        return
    
    # Usar o arquivo mais recente (ordenar por nome, que tem timestamp)
    csv_path = sorted(arquivos_locais)[-1]
    logger.info(f"[CSV] Carregando locais de origem de: {os.path.basename(csv_path)}")

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_local = row['IdInstituicao']
                LOCAIS_ORIGEM_CACHE[id_local] = {
                    'id': id_local,
                    'nome': row['NomFantasia']
                }
        logger.info(f"[CSV] OK - {len(LOCAIS_ORIGEM_CACHE)} locais de origem carregados do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar locais de origem: {e}")

def buscar_medico_por_crm(crm, uf):
    """Busca mÃ©dico no cache por CRM e UF"""
    chave = f"{crm}_{uf}"
    return MEDICOS_CACHE.get(chave)

def buscar_convenio_por_id(id_convenio):
    """Busca convÃªnio no cache por ID"""
    return CONVENIOS_CACHE.get(str(id_convenio))

def buscar_instituicao_por_id(id_instituicao):
    """Busca instituiÃ§Ã£o no cache por ID"""
    return INSTITUICOES_CACHE.get(str(id_instituicao))

def buscar_instituicao_por_nome(nome_busca):
    """
    Busca instituiÃ§Ã£o no cache por nome (busca parcial, case-insensitive)
    
    EstratÃ©gia de busca:
    1. Busca exata
    2. Busca por palavra-chave (primeira palavra significativa)
    3. Busca parcial
    
    Args:
        nome_busca (str): Nome ou parte do nome da instituiÃ§Ã£o
        
    Returns:
        dict: Dados da instituiÃ§Ã£o {'id': int, 'nome': str} ou None se nÃ£o encontrar
    """
    if not nome_busca or not isinstance(nome_busca, str):
        return None
        
    nome_busca_upper = nome_busca.upper().strip()
    logger.info(f"[BuscarInstituicao] ðŸ” Procurando instituiÃ§Ã£o: '{nome_busca}'")
    logger.debug(f"[BuscarInstituicao] Total no cache: {len(INSTITUICOES_CACHE)}")
    
    # 1. Busca exata primeiro
    for id_inst, inst_data in INSTITUICOES_CACHE.items():
        nome_cache = inst_data.get('nome', '').upper()
        if nome_cache == nome_busca_upper:
            logger.info(f"[BuscarInstituicao] âœ… Encontrada (exata): ID={id_inst}, Nome={inst_data.get('nome')}")
            return inst_data
    
    # 2. Busca por palavra-chave (ex: "CASSI - Caixa..." â†’ "CASSI")
    # Pegar primeira palavra significativa (>= 3 caracteres)
    palavras = nome_busca_upper.split()
    palavra_chave = None
    for palavra in palavras:
        palavra_limpa = palavra.strip(',-()[]')
        if len(palavra_limpa) >= 3 and palavra_limpa not in ['DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'EM']:
            palavra_chave = palavra_limpa
            break
    
    if palavra_chave:
        logger.debug(f"[BuscarInstituicao] Palavra-chave extraÃ­da: '{palavra_chave}'")
        for id_inst, inst_data in INSTITUICOES_CACHE.items():
            nome_cache = inst_data.get('nome', '').upper()
            # Busca a palavra no inÃ­cio do nome
            if nome_cache.startswith(palavra_chave):
                logger.info(f"[BuscarInstituicao] âœ… Encontrada (palavra-chave): ID={id_inst}, Nome={inst_data.get('nome')}")
                return inst_data
    
    # 3. Busca parcial (contÃ©m)
    for id_inst, inst_data in INSTITUICOES_CACHE.items():
        nome_cache = inst_data.get('nome', '').upper()
        if nome_busca_upper in nome_cache or nome_cache in nome_busca_upper:
            logger.info(f"[BuscarInstituicao] âœ… Encontrada (parcial): ID={id_inst}, Nome={inst_data.get('nome')}")
            return inst_data
    
    logger.warning(f"[BuscarInstituicao] âš ï¸ InstituiÃ§Ã£o '{nome_busca}' nÃ£o encontrada no cache")
    logger.debug(f"[BuscarInstituicao] Amostra do cache: {list(INSTITUICOES_CACHE.values())[:5]}")
    return None

def obter_id_convenio_default():
    """
    Busca um ID de convÃªnio vÃ¡lido para usar como default
    Prioridade: 1) PARTICULAR, 2) Primeiro do cache

    Returns:
        int: ID do convÃªnio default ou None se cache vazio
    """
    if not CONVENIOS_CACHE:
        logger.warning("[Default] Cache de convÃªnios vazio!")
        return None

    # Tentar encontrar "PARTICULAR" ou similar
    for id_convenio, convenio_data in CONVENIOS_CACHE.items():
        nome = convenio_data.get('nome', '').upper()
        if 'PARTICULAR' in nome or 'PRIVADO' in nome or 'SEM CONVENIO' in nome:
            logger.info(f"[Default] âœ… ConvÃªnio default encontrado: ID={id_convenio}, Nome={convenio_data.get('nome')}")
            return int(id_convenio)

    # Se nÃ£o encontrou PARTICULAR, pegar o primeiro disponÃ­vel
    primeiro_id = list(CONVENIOS_CACHE.keys())[0]
    primeiro_nome = CONVENIOS_CACHE[primeiro_id].get('nome')
    logger.info(f"[Default] âœ… Usando primeiro convÃªnio: ID={primeiro_id}, Nome={primeiro_nome}")
    return int(primeiro_id)

def obter_id_instituicao_default():
    """
    Busca um ID de instituiÃ§Ã£o vÃ¡lido para usar como default

    Returns:
        int: ID da instituiÃ§Ã£o default ou None se cache vazio
    """
    if not INSTITUICOES_CACHE:
        logger.warning("[Default] Cache de instituiÃ§Ãµes vazio!")
        return None

    # Pegar a primeira disponÃ­vel
    primeiro_id = list(INSTITUICOES_CACHE.keys())[0]
    primeiro_nome = INSTITUICOES_CACHE[primeiro_id].get('nome')
    logger.info(f"[Default] âœ… InstituiÃ§Ã£o default: ID={primeiro_id}, Nome={primeiro_nome}")
    return int(primeiro_id)

def buscar_instituicao_por_nome(nome_busca):
    """
    Busca instituiÃ§Ã£o (fonte pagadora) por nome (busca parcial, case-insensitive)
    
    Args:
        nome_busca (str): Nome ou parte do nome da instituiÃ§Ã£o
    
    Returns:
        dict: {'id': int, 'nome': str} ou None se nÃ£o encontrar
    """
    if not nome_busca or not INSTITUICOES_CACHE:
        return None
    
    nome_busca_upper = nome_busca.upper().strip()
    
    # Busca exata primeiro
    for id_inst, dados_inst in INSTITUICOES_CACHE.items():
        if dados_inst.get('nome', '').upper() == nome_busca_upper:
            logger.info(f"[BuscarInstituicao] âœ… Match exato: ID={id_inst}, Nome={dados_inst.get('nome')}")
            return {'id': int(id_inst), 'nome': dados_inst.get('nome')}
    
    # Busca parcial (contÃ©m)
    for id_inst, dados_inst in INSTITUICOES_CACHE.items():
        nome_inst = dados_inst.get('nome', '').upper()
        if nome_busca_upper in nome_inst:
            logger.info(f"[BuscarInstituicao] âœ… Match parcial: ID={id_inst}, Nome={dados_inst.get('nome')}")
            return {'id': int(id_inst), 'nome': dados_inst.get('nome')}
    
    logger.warning(f"[BuscarInstituicao] âš ï¸ InstituiÃ§Ã£o '{nome_busca}' nÃ£o encontrada no cache")
    return None

def obter_id_medico_default():
    """
    Busca um ID de mÃ©dico vÃ¡lido para usar como default

    Returns:
        int: ID do mÃ©dico default ou None se cache vazio
    """
    if not MEDICOS_CACHE:
        logger.warning("[Default] Cache de mÃ©dicos vazio!")
        return None

    # Pegar o primeiro disponÃ­vel
    primeiro_medico = list(MEDICOS_CACHE.values())[0]
    primeiro_id = primeiro_medico.get('id')
    primeiro_nome = primeiro_medico.get('nome')
    logger.info(f"[Default] âœ… MÃ©dico default: ID={primeiro_id}, Nome={primeiro_nome}")
    return int(primeiro_id)

def _buscar_id_por_nome_convenio(nome_convenio):
    """Helper: Busca ID do convÃªnio nos CSVs usando o NOME (lookup reverso)"""
    logger.info(f"[LookupReverso] Buscando ID para convenio: '{nome_convenio}'")
    
    if not nome_convenio or nome_convenio.strip() == '':
        logger.warning(f"[LookupReverso] Nome vazio fornecido")
        return None
    
    nome_normalizado = nome_convenio.strip().upper()
    
    # Tentativa 1: Busca exata
    for id_conv, dados in CONVENIOS_CACHE.items():
        nome_cache = dados.get('nome', '').strip().upper()
        if nome_cache == nome_normalizado:
            logger.info(f"[LookupReverso] OK Convenio '{nome_convenio}' encontrado (exato)! ID: {id_conv}")
            return id_conv
    
    # Tentativa 2: Busca parcial (contÃ©m)
    # Remove caracteres especiais e espaÃ§os extras
    import re
    nome_limpo = re.sub(r'[^\w\s]', '', nome_normalizado).strip()
    nome_limpo = re.sub(r'\s+', ' ', nome_limpo)
    
    logger.info(f"[LookupReverso] Tentando busca parcial com: '{nome_limpo}'")
    
    for id_conv, dados in CONVENIOS_CACHE.items():
        nome_cache_original = dados.get('nome', '').strip().upper()
        nome_cache_limpo = re.sub(r'[^\w\s]', '', nome_cache_original).strip()
        nome_cache_limpo = re.sub(r'\s+', ' ', nome_cache_limpo)
        
        if nome_limpo == nome_cache_limpo:
            logger.info(f"[LookupReverso] OK Convenio '{nome_convenio}' encontrado (normalizado)! ID: {id_conv}, Nome CSV: '{nome_cache_original}'")
            return id_conv
    
    logger.warning(f"[LookupReverso] ERRO Convenio '{nome_convenio}' NAO encontrado no cache")
    logger.warning(f"[LookupReverso] INFO Total de convenios no cache: {len(CONVENIOS_CACHE)}")
    return None

def _buscar_id_por_nome_instituicao(nome_instituicao):
    """Helper: Busca ID da instituiÃ§Ã£o nos CSVs usando o NOME (lookup reverso)"""
    logger.info(f"[LookupReverso] Buscando ID para instituicao: '{nome_instituicao}'")
    
    if not nome_instituicao or nome_instituicao.strip() == '':
        logger.warning(f"[LookupReverso] Nome vazio fornecido")
        return None
    
    nome_normalizado = nome_instituicao.strip().upper()
    
    # Tentativa 1: Busca exata
    for id_inst, dados in INSTITUICOES_CACHE.items():
        nome_cache = dados.get('nome', '').strip().upper()
        if nome_cache == nome_normalizado:
            logger.info(f"[LookupReverso] OK Instituicao '{nome_instituicao}' encontrada (exata)! ID: {id_inst}")
            return id_inst
    
    # Tentativa 2: Busca parcial (contÃ©m)
    # Remove caracteres especiais e espaÃ§os extras
    import re
    nome_limpo = re.sub(r'[^\w\s]', '', nome_normalizado).strip()
    nome_limpo = re.sub(r'\s+', ' ', nome_limpo)
    
    logger.info(f"[LookupReverso] Tentando busca parcial com: '{nome_limpo}'")
    
    for id_inst, dados in INSTITUICOES_CACHE.items():
        nome_cache_original = dados.get('nome', '').strip().upper()
        nome_cache_limpo = re.sub(r'[^\w\s]', '', nome_cache_original).strip()
        nome_cache_limpo = re.sub(r'\s+', ' ', nome_cache_limpo)
        
        if nome_limpo == nome_cache_limpo:
            logger.info(f"[LookupReverso] OK Instituicao '{nome_instituicao}' encontrada (normalizada)! ID: {id_inst}, Nome CSV: '{nome_cache_original}'")
            return id_inst
    
    logger.warning(f"[LookupReverso] ERRO Instituicao '{nome_instituicao}' NAO encontrada no cache")
    logger.warning(f"[LookupReverso] INFO Total de instituicoes no cache: {len(INSTITUICOES_CACHE)}")
    return None

def _buscar_convenio_nome(id_convenio):
    """Helper: Busca nome do convÃªnio nos CSVs usando o ID"""
    logger.info(f"[Helper] ðŸ” _buscar_convenio_nome chamado com ID: {id_convenio} (tipo: {type(id_convenio).__name__})")
    
    # Verificar se ID Ã© None, 0, vazio ou string vazia
    if id_convenio is None or id_convenio == '' or id_convenio == 0:
        logger.warning(f"[Helper] âš ï¸ ID invÃ¡lido (None/vazio/zero): {id_convenio}")
        logger.warning(f"[Helper] ðŸ’¡ POSSÃVEL CAUSA: Banco de dados nÃ£o tem IdConvenio para esta requisiÃ§Ã£o")
        logger.warning(f"[Helper] ðŸ’¡ SOLUÃ‡ÃƒO: Verificar se a requisiÃ§Ã£o foi salva no apLIS com convÃªnio")
        return None
    
    try:
        logger.debug(f"[Helper] Total de convÃªnios em cache: {len(CONVENIOS_CACHE)}")
        if len(CONVENIOS_CACHE) == 0:
            logger.error(f"[Helper] âŒ CACHE DE CONVÃŠNIOS VAZIO! CSV nÃ£o foi carregado corretamente")
            logger.error(f"[Helper] ðŸ’¡ Verifique se o arquivo dados/convenios_extraidos_*.csv existe")
            return None
        
        logger.debug(f"[Helper] Primeiras 5 chaves do cache: {list(CONVENIOS_CACHE.keys())[:5]}")

        # Tentar buscar com o ID original
        convenio = buscar_convenio_por_id(id_convenio)
        if convenio:
            nome = convenio.get('nome')
            logger.info(f"[Helper] âœ… ConvÃªnio ID {id_convenio} ENCONTRADO: {nome}")
            return nome
        
        # Tentar conversÃµes de tipo (int â†’ str, str â†’ int)
        id_str = str(id_convenio)
        convenio_str = CONVENIOS_CACHE.get(id_str)
        if convenio_str:
            nome = convenio_str.get('nome')
            logger.info(f"[Helper] âœ… ConvÃªnio ID {id_convenio} ENCONTRADO (como string): {nome}")
            return nome
        
        # Se for string numÃ©rica, tentar como int
        try:
            id_int = int(id_convenio)
            convenio_int = CONVENIOS_CACHE.get(str(id_int))
            if convenio_int:
                nome = convenio_int.get('nome')
                logger.info(f"[Helper] âœ… ConvÃªnio ID {id_convenio} ENCONTRADO (convertido para int): {nome}")
                return nome
        except (ValueError, TypeError):
            pass

        # Se chegou aqui, nÃ£o encontrou
        logger.warning(f"[Helper] âŒ ConvÃªnio ID {id_convenio} NÃƒO encontrado no cache")
        logger.warning(f"[Helper] IDs disponÃ­veis no cache (primeiros 20): {list(CONVENIOS_CACHE.keys())[:20]}")
        logger.warning(f"[Helper] ðŸ’¡ POSSÃVEL CAUSA: ID do banco nÃ£o corresponde aos IDs do CSV")
        logger.warning(f"[Helper] ðŸ’¡ SUGESTÃƒO: Execute backend/extrair_convenios.py para atualizar o CSV")
        
    except Exception as e:
        logger.error(f"[Helper] ðŸ’¥ Erro inesperado: {e}")
        import traceback
        logger.error(traceback.format_exc())

    logger.info(f"[Helper] ðŸ“¤ Retornando None (nÃ£o encontrado)")
    return None

def _buscar_instituicao_nome(id_instituicao):
    """Helper: Busca nome da instituiÃ§Ã£o nos CSVs usando o ID"""
    logger.info(f"[Helper] ðŸ” _buscar_instituicao_nome chamado com ID: {id_instituicao} (tipo: {type(id_instituicao).__name__})")
    
    # Verificar se ID Ã© None, 0, vazio ou string vazia
    if id_instituicao is None or id_instituicao == '' or id_instituicao == 0:
        logger.warning(f"[Helper] âš ï¸ ID invÃ¡lido (None/vazio/zero): {id_instituicao}")
        logger.warning(f"[Helper] ðŸ’¡ POSSÃVEL CAUSA: Banco de dados nÃ£o tem IdFontePagadora/IdLocalOrigem para esta requisiÃ§Ã£o")
        logger.warning(f"[Helper] ðŸ’¡ SOLUÃ‡ÃƒO: Verificar se a requisiÃ§Ã£o foi salva no apLIS com fonte pagadora/local origem")
        return None
    
    try:
        logger.debug(f"[Helper] Total de instituiÃ§Ãµes em cache: {len(INSTITUICOES_CACHE)}")
        if len(INSTITUICOES_CACHE) == 0:
            logger.error(f"[Helper] âŒ CACHE DE INSTITUIÃ‡Ã•ES VAZIO! CSV nÃ£o foi carregado corretamente")
            logger.error(f"[Helper] ðŸ’¡ Verifique se o arquivo dados/instituicoes_extraidas_*.csv existe")
            logger.error(f"[Helper] ðŸ’¡ Execute: python backend/extrair_instituicoes.py")
            # NÃ£o retornar None ainda - tentar fallback do banco
        else:
            logger.debug(f"[Helper] Primeiras 5 chaves do cache: {list(INSTITUICOES_CACHE.keys())[:5]}")

            # Tentar buscar com o ID original
            instituicao = buscar_instituicao_por_id(id_instituicao)
            if instituicao:
                nome = instituicao.get('nome')
                logger.info(f"[Helper] âœ… InstituiÃ§Ã£o ID {id_instituicao} ENCONTRADA no CSV: {nome}")
                return nome
            
            # Tentar conversÃµes de tipo (int â†’ str, str â†’ int)
            id_str = str(id_instituicao)
            instituicao_str = INSTITUICOES_CACHE.get(id_str)
            if instituicao_str:
                nome = instituicao_str.get('nome')
                logger.info(f"[Helper] âœ… InstituiÃ§Ã£o ID {id_instituicao} ENCONTRADA no CSV (como string): {nome}")
                return nome
            
            # Se for string numÃ©rica, tentar como int
            try:
                id_int = int(id_instituicao)
                instituicao_int = INSTITUICOES_CACHE.get(str(id_int))
                if instituicao_int:
                    nome = instituicao_int.get('nome')
                    logger.info(f"[Helper] âœ… InstituiÃ§Ã£o ID {id_instituicao} ENCONTRADA no CSV (convertido para int): {nome}")
                    return nome
            except (ValueError, TypeError):
                pass

        # Nao encontrou no CSV - FALLBACK: buscar NomFantasia direto em fatinstituicao
        logger.warning(f"[Helper] Instituicao ID {id_instituicao} NAO encontrada no CSV")
        logger.info(f"[Helper] FALLBACK: Buscando NomFantasia em fatinstituicao...")

        try:
            connection = pymysql.connect(**DB_CONFIG)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            cursor.execute(
                "SELECT NomFantasia AS nome FROM newdb.fatinstituicao WHERE IdInstituicao = %s LIMIT 1",
                (id_instituicao,)
            )
            resultado = cursor.fetchone()

            cursor.close()
            connection.close()

            if resultado and resultado.get('nome'):
                nome_banco = resultado.get('nome')
                logger.info(f"[Helper] Instituicao ID {id_instituicao} encontrada em fatinstituicao: {nome_banco}")
                return nome_banco
            else:
                logger.error(f"[Helper] Instituicao ID {id_instituicao} NAO encontrada em fatinstituicao")

        except Exception as db_error:
            logger.error(f"[Helper] Erro ao buscar em fatinstituicao: {db_error}")

    except Exception as e:
        logger.error(f"[Helper] Erro inesperado: {e}")

    return None

# Carregar CSVs na inicializaÃ§Ã£o
logger.info("[INIT] Carregando dados dos CSVs...")
carregar_medicos_csv()
carregar_convenios_csv()
carregar_instituicoes_csv()
carregar_locais_origem_csv()

# Configurações apLIS - USAR VARIÁVEIS DE AMBIENTE
APLIS_URL = os.getenv('APLIS_BASE_URL', 'https://lab.aplis.inf.br/api/integracao.php')
APLIS_USERNAME = os.getenv('APLIS_USUARIO', 'api.lab')
APLIS_PASSWORD = os.getenv('APLIS_SENHA', '')  # âš ï¸ CONFIGURE NO .env
APLIS_HEADERS = {"Content-Type": "application/json"}

# ConfiguraÃ§Ãµes AWS S3
S3_CONFIG = {
    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
    'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
    'region_name': os.getenv('AWS_REGION', 'sa-east-1')
}
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'aplis2')


def get_s3_client():
    """Cria cliente S3"""
    try:
        s3 = boto3.client('s3', **S3_CONFIG)
        return s3
    except Exception as e:
        print(f"Erro ao criar cliente S3: {e}")
        return None


def fazer_requisicao_aplis(cmd, dat, aplis_usuario=None, aplis_senha=None):
    """
    FunÃ§Ã£o genÃ©rica para fazer requisiÃ§Ãµes ao apLIS usando a metodologia requisicaoListar

    Args:
        cmd (str): Comando a executar (ex: "requisicaoListar", "admissaoSalvar")
        dat (dict): Dados a enviar no campo "dat"
        aplis_usuario (str, optional): UsuÃ¡rio do apLIS (usa padrÃ£o do .env se nÃ£o fornecido)
        aplis_senha (str, optional): Senha do apLIS (usa padrÃ£o do .env se nÃ£o fornecido)

    Returns:
        dict: Resposta da API apLIS
    """
    # Usar credenciais fornecidas ou padrÃ£o do .env
    usuario = aplis_usuario if aplis_usuario else APLIS_USERNAME
    senha = aplis_senha if aplis_senha else APLIS_PASSWORD

    payload = {
        "ver": 1,
        "cmd": cmd,
        "dat": dat
    }

    data = json.dumps(payload)
    logger.info(f"[apLIS] Enviando requisiÃ§Ã£o: {cmd}")
    logger.info(f"[apLIS] UsuÃ¡rio apLIS: {usuario}")
    logger.info(f"[apLIS] Payload completo: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(
            APLIS_URL,
            auth=(usuario, senha),
            headers=APLIS_HEADERS,
            data=data
        )

        logger.info(f"[apLIS] Status Code: {response.status_code}")

        try:
            resposta_json = response.json()
            logger.info(f"[apLIS] Resposta JSON completa: {json.dumps(resposta_json, indent=2, ensure_ascii=False)}")

            if resposta_json.get("dat") and resposta_json["dat"].get("sucesso") == 1:
                logger.info(f"[apLIS] RequisiÃ§Ã£o bem-sucedida para comando: {cmd}")
                return resposta_json
            else:
                logger.warning(f"[apLIS] Resposta com sucesso != 1: {resposta_json}")
                return resposta_json

        except ValueError:
            logger.error(f"[apLIS] Resposta nÃ£o estÃ¡ em JSON: {response.text}")
            return {"erro": "Resposta invÃ¡lida do apLIS", "texto": response.text, "sucesso": 0, "dat": {}}

    except requests.exceptions.RequestException as e:
        logger.error(f"[apLIS] Erro na requisiÃ§Ã£o: {str(e)}")
        return {"erro": f"Erro na requisiÃ§Ã£o: {str(e)}", "sucesso": 0, "dat": {}}
    except Exception as e:
        logger.error(f"[apLIS] Erro inesperado: {str(e)}")
        return {"erro": f"Erro inesperado: {str(e)}", "sucesso": 0, "dat": {}}


def extrair_credenciais_usuario(request):
    """
    Extrai credenciais do apLIS do usuÃ¡rio a partir do corpo da requisiÃ§Ã£o.

    Args:
        request: Request do Flask

    Returns:
        tuple: (aplis_usuario, aplis_senha) ou (None, None) se nÃ£o encontradas
    """
    try:
        dados = request.get_json()
        if not dados:
            return None, None

        aplis_usuario = dados.get('aplis_usuario')
        aplis_senha = dados.get('aplis_senha')

        logger.info(f"[AUTH] Credenciais apLIS extraÃ­das: usuario={aplis_usuario}")

        return aplis_usuario, aplis_senha
    except Exception as e:
        logger.error(f"[AUTH] Erro ao extrair credenciais: {e}")
        return None, None


def consultar_cpf_receita_federal(cpf, data_nascimento):
    """
    Consulta CPF na API da Receita Federal (HubDoDesenvolvedor)

    Args:
        cpf (str): CPF no formato XXX.XXX.XXX-XX ou apenas nÃºmeros
        data_nascimento (str): Data de nascimento no formato DD/MM/YYYY ou YYYY-MM-DD

    Returns:
        dict: Dados validados da Receita Federal ou None se houver erro
    """
    try:
        # Remove formataÃ§Ã£o do CPF (pontos e traÃ§os)
        cpf_limpo = cpf.replace(".", "").replace("-", "").replace("/", "").strip() if cpf else ""

        if not cpf_limpo or len(cpf_limpo) != 11:
            logger.warning(f"[CPF_API] CPF invalido ou vazio: {cpf}")
            return None

        # IMPORTANTE: A API funciona melhor SEM a data de nascimento (enviar vazia)
        # Se enviar data, a API pode rejeitar com "Parametro Invalido"
        data_param = ""

        # Monta a URL com os parÃ¢metros (data sempre vazia)
        url = f"{CPF_API_BASE_URL}?cpf={cpf_limpo}&data={data_param}&token={CPF_API_TOKEN}"

        logger.info(f"[CPF_API] Consultando CPF: {cpf_limpo}")
        
        # Headers para evitar bloqueio de bot (User-Agent)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        # Faz a requisiÃ§Ã£o com Retry (3 tentativas)
        response = None
        last_error = None
        
        for i in range(3):
            try:
                logger.debug(f"[CPF_API] Tentativa {i+1}/3...")
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    break
                logger.warning(f"[CPF_API] Tentativa {i+1} falhou: Status {response.status_code}")
                time.sleep(1)
            except Exception as e:
                last_error = e
                logger.warning(f"[CPF_API] Tentativa {i+1} erro: {str(e)}")
                time.sleep(1)

        if response is None:
            logger.error(f"[CPF_API] Falha total na conexÃ£o. Ãšltimo erro: {last_error}")
            return None

        logger.debug(f"[CPF_API] Status Code: {response.status_code}")

        # Tenta decodificar o JSON
        resultado = response.json()

        # Verifica se a consulta foi bem-sucedida
        if resultado.get("return") == "OK":
            result_data = resultado.get("result", {})

            logger.info(f"[CPF_API] [OK] Consulta bem-sucedida!")
            logger.info(f"[CPF_API]   Nome: {result_data.get('nome_da_pf')}")
            logger.info(f"[CPF_API]   CPF: {result_data.get('numero_de_cpf')}")
            logger.info(f"[CPF_API]   Data Nascimento: {result_data.get('data_nascimento')}")
            logger.info(f"[CPF_API]   Situacao: {result_data.get('situacao_cadastral')}")

            # Formatar data de nascimento para DD/MM/YYYY (garantir formato numÃ©rico)
            data_nasc_formatada = result_data.get("data_nascimento", "")
            if data_nasc_formatada:
                # Se vier no formato YYYY-MM-DD, converter para DD/MM/YYYY
                if len(data_nasc_formatada) == 10 and '-' in data_nasc_formatada:
                    try:
                        partes = data_nasc_formatada.split('-')
                        if len(partes) == 3:
                            data_nasc_formatada = f"{partes[2]}/{partes[1]}/{partes[0]}"
                            logger.info(f"[CPF_API]   Data formatada: {data_nasc_formatada}")
                    except:
                        pass

            return {
                "nome": result_data.get("nome_da_pf"),
                "cpf": result_data.get("numero_de_cpf"),
                "data_nascimento": data_nasc_formatada,
                "situacao_cadastral": result_data.get("situacao_cadastral"),
                "data_inscricao": result_data.get("data_inscricao"),
                "valido": True
            }
        else:
            logger.warning(f"[CPF_API] Consulta falhou: {resultado.get('msg', resultado.get('message', 'Sem dados disponiveis'))}")
            return None

    except requests.exceptions.Timeout:
        logger.error("[CPF_API] Timeout na requisicao (tempo limite excedido)")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[CPF_API] Erro na requisicao: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"[CPF_API] Erro ao decodificar JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"[CPF_API] Erro inesperado: {e}")
        return None


def validar_e_corrigir_dados_cpf(dados_aplis, dados_sistema_antigo=None):
    """
    Valida dados do CPF com a Receita Federal e corrige se necessÃ¡rio.
    Prioriza dados da Receita Federal sobre dados do apLIS.

    Args:
        dados_aplis (dict): Dados vindos do apLIS
        dados_sistema_antigo (dict): Dados do sistema antigo (opcional)

    Returns:
        dict: Dados corrigidos/validados com informaÃ§Ãµes da Receita Federal
    """
    try:
        cpf = dados_aplis.get("CPF")
        data_nascimento = None

        # Tentar obter data de nascimento do sistema antigo primeiro
        if dados_sistema_antigo and dados_sistema_antigo.get("dtaNasc"):
            data_nascimento = dados_sistema_antigo.get("dtaNasc")

        # Se nÃ£o tem CPF, nÃ£o hÃ¡ o que validar
        if not cpf:
            logger.warning("[ValidarCPF] Sem CPF para validar")
            return {
                "dados_corrigidos": False,
                "fonte_dados": "aplis",
                "dados": {
                    "nome": dados_aplis.get("NomPaciente"),
                    "cpf": cpf,
                    "dtaNasc": data_nascimento
                }
            }

        # Consultar Receita Federal
        logger.info(f"[ValidarCPF] Iniciando validaÃ§Ã£o de CPF: {cpf}")
        dados_receita = consultar_cpf_receita_federal(cpf, data_nascimento)

        if not dados_receita:
            logger.warning("[ValidarCPF] NÃ£o foi possÃ­vel validar CPF na Receita Federal")
            return {
                "dados_corrigidos": False,
                "fonte_dados": "aplis",
                "aviso": "NÃ£o foi possÃ­vel validar CPF na Receita Federal",
                "dados": {
                    "nome": dados_aplis.get("NomPaciente"),
                    "cpf": cpf,
                    "dtaNasc": data_nascimento
                }
            }

        # Comparar dados
        nome_aplis = dados_aplis.get("NomPaciente", "").strip().upper()
        nome_receita = dados_receita.get("nome", "").strip().upper()
        cpf_receita = dados_receita.get("cpf", "").replace(".", "").replace("-", "")
        data_nasc_receita = dados_receita.get("data_nascimento")

        # Verificar se hÃ¡ divergÃªncias
        divergencias = []
        dados_corrigidos = False

        # Comparar nomes (ignora maiÃºsculas/minÃºsculas e espaÃ§os extras)
        if nome_aplis and nome_receita and nome_aplis != nome_receita:
            divergencias.append(f"Nome: apLIS='{dados_aplis.get('NomPaciente')}' â†’ Receita='{dados_receita.get('nome')}'")
            dados_corrigidos = True

        # Comparar CPFs
        cpf_aplis_limpo = cpf.replace(".", "").replace("-", "")
        if cpf_aplis_limpo != cpf_receita:
            divergencias.append(f"CPF: apLIS='{cpf}' â†’ Receita='{dados_receita.get('cpf')}'")
            dados_corrigidos = True

        # Comparar data de nascimento
        if data_nascimento and data_nasc_receita:
            # Normalizar formatos para comparaÃ§Ã£o
            data_aplis_norm = data_nascimento.replace("/", "").replace("-", "")
            data_receita_norm = data_nasc_receita.replace("/", "").replace("-", "")

            if data_aplis_norm != data_receita_norm:
                divergencias.append(f"Data Nasc: Sistema='{data_nascimento}' â†’ Receita='{data_nasc_receita}'")
                dados_corrigidos = True

        # Log das divergÃªncias
        if divergencias:
            logger.warning(f"[ValidarCPF] âš ï¸ DIVERGÃŠNCIAS ENCONTRADAS:")
            for div in divergencias:
                logger.warning(f"[ValidarCPF]   - {div}")
            logger.info(f"[ValidarCPF] âœ… Dados serÃ£o corrigidos com informaÃ§Ãµes da Receita Federal")
        else:
            logger.info(f"[ValidarCPF] âœ… Dados conferem com a Receita Federal")

        # Retornar dados PRIORIZANDO Receita Federal
        return {
            "dados_corrigidos": dados_corrigidos,
            "fonte_dados": "receita_federal",
            "divergencias": divergencias if divergencias else None,
            "situacao_cadastral": dados_receita.get("situacao_cadastral"),
            "dados": {
                "nome": dados_receita.get("nome"),  # PRIORIDADE: Receita Federal
                "cpf": dados_receita.get("cpf"),    # PRIORIDADE: Receita Federal
                "dtaNasc": dados_receita.get("data_nascimento")  # PRIORIDADE: Receita Federal
            },
            "dados_originais_aplis": {
                "nome": dados_aplis.get("NomPaciente"),
                "cpf": cpf,
                "dtaNasc": data_nascimento
            },
            # Dados comparativos para exibiÃ§Ã£o
            "comparacao": {
                "nome": {
                    "sistema": dados_aplis.get("NomPaciente"),
                    "receita_federal": dados_receita.get("nome"),
                    "divergente": nome_aplis != nome_receita if nome_aplis and nome_receita else False
                },
                "cpf": {
                    "sistema": cpf,
                    "receita_federal": dados_receita.get("cpf"),
                    "divergente": cpf.replace(".", "").replace("-", "") != cpf_receita if cpf else False
                },
                "data_nascimento": {
                    "sistema": data_nascimento,
                    "receita_federal": dados_receita.get("data_nascimento"),
                    "divergente": data_nascimento and dados_receita.get("data_nascimento") and 
                                 data_nascimento.replace("/", "").replace("-", "") != 
                                 dados_receita.get("data_nascimento", "").replace("/", "").replace("-", "")
                }
            }
        }

    except Exception as e:
        logger.error(f"[ValidarCPF] âŒ Erro ao validar CPF: {e}")
        return {
            "dados_corrigidos": False,
            "fonte_dados": "aplis",
            "erro": str(e),
            "dados": {
                "nome": dados_aplis.get("NomPaciente"),
                "cpf": dados_aplis.get("CPF"),
                "dtaNasc": dados_sistema_antigo.get("dtaNasc") if dados_sistema_antigo else None
            }
        }


def salvar_admissao_aplis(dados_admissao, aplis_usuario=None, aplis_senha=None):
    """
    Salva uma admissÃ£o/requisiÃ§Ã£o no apLIS usando a nova metodologia genÃ©rica

    Args:
        dados_admissao (dict): Dados da admissÃ£o
        aplis_usuario (str, optional): UsuÃ¡rio do apLIS
        aplis_senha (str, optional): Senha do apLIS
    """
    logger.info(f"[AdmissÃ£o] Salvando admissÃ£o com dados: {len(str(dados_admissao))} bytes")
    logger.info(f"[AdmissÃ£o] UsuÃ¡rio apLIS: {aplis_usuario or 'PADRÃƒO'}")
    return fazer_requisicao_aplis("admissaoSalvar", dados_admissao, aplis_usuario, aplis_senha)


def buscar_dados_paciente_sistema_antigo(cod_paciente=None, cpf=None):
    """
    Busca dados COMPLETOS do paciente buscando requisiÃ§Ãµes ANTIGAS do mesmo paciente

    ESTRATÃ‰GIA: Como o `requisicaoListar` do sistema novo nÃ£o retorna dados completos
    do paciente (dtaNasc, RG, endereÃ§o), buscamos requisiÃ§Ãµes antigas (com 1+ dia de atraso)
    para obter esses dados complementares que podem ter sido salvos anteriormente.

    Dados que buscamos:
    - Data de nascimento
    - RG
    - Sexo
    - Telefone
    - EndereÃ§o completo

    Args:
        cod_paciente (str): CÃ³digo do paciente
        cpf (str): CPF do paciente

    Returns:
        dict: Dados completos do paciente ou None se nÃ£o encontrar
    """
    try:
        logger.info(f"[SistemaComplementar] Buscando dados histÃ³ricos do paciente: codPaciente={cod_paciente}, cpf={cpf}")

        # IMPORTANTE: Como requisicaoListar do sistema NOVO nÃ£o retorna dados completos
        # do paciente, vamos buscar usando requisicaoResultado ou fazer busca ampla
        # em requisiÃ§Ãµes antigas do paciente

        if not cod_paciente:
            logger.warning(f"[SistemaComplementar] CÃ³digo do paciente nÃ£o fornecido, impossÃ­vel buscar dados")
            return None

        # Buscar requisiÃ§Ãµes antigas do paciente (Ãºltimos 2 anos)
        hoje = datetime.now()
        periodo_fim = (hoje - timedelta(days=1)).strftime("%Y-%m-%d")  # Ontem (dados com atraso)
        periodo_ini = (hoje - timedelta(days=730)).strftime("%Y-%m-%d")  # 2 anos atrÃ¡s

        dat = {
            "tipoData": 1,  # Data de solicitaÃ§Ã£o
            "periodoIni": periodo_ini,
            "periodoFim": periodo_fim,
            "idPaciente": int(cod_paciente),
            "ordenar": "DtaSolicitacao",
            "pagina": 1,
            "tamanho": 1  # Apenas a mais recente
        }

        logger.debug(f"[SistemaComplementar] Buscando requisiÃ§Ãµes antigas: {dat}")

        # Fazer requisiÃ§Ã£o usando requisicaoListar (modo usuÃ¡rios internos)
        resposta = fazer_requisicao_aplis("requisicaoListar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            lista_requisicoes = resposta.get("dat", {}).get("lista", [])

            if lista_requisicoes and len(lista_requisicoes) > 0:
                # Pegar a requisiÃ§Ã£o mais recente
                req_antiga = lista_requisicoes[0]
                cod_req_antiga = req_antiga.get("CodRequisicao")

                logger.info(f"[SistemaComplementar] âœ… Encontrada requisiÃ§Ã£o antiga: {cod_req_antiga}")

                # Agora buscar dados COMPLETOS usando requisicaoResultado
                # que retorna dados completos do paciente!
                logger.info(f"[SistemaComplementar] Buscando dados completos via requisicaoResultado...")

                dat_resultado = {
                    "codRequisicao": cod_req_antiga
                }

                resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

                if resposta_resultado.get("dat", {}).get("sucesso") == 1:
                    dados_resultado = resposta_resultado.get("dat", {})
                    paciente_completo = dados_resultado.get("paciente", {})

                    logger.info(f"[SistemaComplementar] âœ… Dados completos obtidos via requisicaoResultado!")
                    logger.debug(f"[SistemaComplementar] Dados paciente RAW: {json.dumps(paciente_completo, indent=2, ensure_ascii=False)[:1000]}")

                    # Verificar todos os campos disponÃ­veis no paciente_completo
                    logger.info(f"[SistemaComplementar] ðŸ” Campos disponÃ­veis em paciente_completo: {list(paciente_completo.keys())}")

                    # Extrair dados do paciente
                    # Tentar pegar RG, telefone e endereÃ§o se existirem
                    dados_paciente = {
                        "dtaNasc": paciente_completo.get("dtaNasc"),
                        "sexo": paciente_completo.get("sexo"),
                        "rg": paciente_completo.get("rg") or paciente_completo.get("RG") or paciente_completo.get("numIdentidade"),
                        "telCelular": paciente_completo.get("telCelular") or paciente_completo.get("telefone") or paciente_completo.get("fone"),
                        "endereco": {
                            "logradouro": paciente_completo.get("logradouro") or paciente_completo.get("endereco"),
                            "numEndereco": paciente_completo.get("numEndereco") or paciente_completo.get("numero"),
                            "bairro": paciente_completo.get("bairro"),
                            "cidade": paciente_completo.get("cidade") or paciente_completo.get("municipio"),
                            "uf": paciente_completo.get("uf") or paciente_completo.get("estado"),
                            "cep": paciente_completo.get("cep")
                        }
                    }

                    logger.info(f"[SistemaComplementar] Campos extraÃ­dos: dtaNasc={dados_paciente.get('dtaNasc')}, "
                              f"sexo={dados_paciente.get('sexo')}")

                    # Se encontrou pelo menos data de nascimento, retornar
                    if dados_paciente.get("dtaNasc"):
                        return dados_paciente
                    else:
                        logger.warning(f"[SistemaComplementar] Dados incompletos, retornando None")
                        return None
                else:
                    logger.warning(f"[SistemaComplementar] Erro ao buscar requisicaoResultado: {resposta_resultado}")
                    return None
            else:
                logger.info(f"[SistemaComplementar] Nenhuma requisiÃ§Ã£o antiga encontrada para o paciente")
                return None
        else:
            logger.warning(f"[SistemaComplementar] Resposta sem sucesso: {resposta}")
            return None

    except Exception as e:
        logger.error(f"[SistemaComplementar] Erro ao buscar dados: {str(e)}")
        import traceback
        logger.error(f"[SistemaComplementar] Traceback: {traceback.format_exc()}")
        return None


def listar_requisicoes_aplis(id_evento, periodo_ini, periodo_fim, ordenar="IdRequisicao", paginaAtual=1):
    """
    Lista requisiÃ§Ãµes do apLIS usando requisicaoListar
    
    Args:
        id_evento (str): ID do evento
        periodo_ini (str): Data inicial (YYYY-MM-DD)
        periodo_fim (str): Data final (YYYY-MM-DD)
        ordenar (str): Campo para ordenaÃ§Ã£o (padrÃ£o: IdRequisicao)
        paginaAtual (int): NÃºmero da pÃ¡gina a buscar (padrÃ£o: 1)
    
    Returns:
        dict: Resposta com requisiÃ§Ãµes
    """
    dat = {
        "ordenar": ordenar,
        "idEvento": str(id_evento),
        "periodoIni": periodo_ini,
        "periodoFim": periodo_fim,
        "paginaAtual": paginaAtual  # â† ParÃ¢metro de paginaÃ§Ã£o
    }
    
    logger.info(f"[Listagem] Listando requisiÃ§Ãµes do evento {id_evento} de {periodo_ini} a {periodo_fim} (pÃ¡gina {paginaAtual})")
    return fazer_requisicao_aplis("requisicaoListar", dat)


def listar_requisicoes_detalhadas(id_evento, periodo_ini, periodo_fim, enriquecer=True):
    """
    Lista requisiÃ§Ãµes do apLIS com dados PRIMÃRIOS + complementares enriquecidos
    
    â­ AGORA BUSCA TODAS AS PÃGINAS - NÃ£o fica limitado aos primeiros 50 registros!
    
    Esta funÃ§Ã£o integra as duas metodologias:
    1. PRIMÃRIA (requisicaoListar): Traz dados bÃ¡sicos e importantes
       - CÃ³digo da requisiÃ§Ã£o
       - CPF do paciente
       - Nome do paciente
       - Data da coleta
       - ID do mÃ©dico
       
    2. COMPLEMENTAR (enriquecimento): Adiciona informaÃ§Ãµes complementares
       - Dados do mÃ©dico completos
       - Convenio
       - Fonte pagadora
       - Local de origem
       - Dados clÃ­nicos
    
    Args:
        id_evento (str): ID do evento
        periodo_ini (str): Data inicial (YYYY-MM-DD)
        periodo_fim (str): Data final (YYYY-MM-DD)
        enriquecer (bool): Se deve buscar dados complementares (padrÃ£o: True)
    
    Returns:
        dict: Lista de requisiÃ§Ãµes com dados primÃ¡rios e complementares (TODAS as pÃ¡ginas)
    """
    try:
        logger.info(f"[ListagemDetalhada] Iniciando busca: evento={id_evento}, perÃ­odo={periodo_ini} a {periodo_fim}")
        
        # PASSO 1: Obter TODAS as pÃ¡ginas de requisiÃ§Ãµes
        lista_requisicoes_total = []
        pagina_atual = 1
        
        while True:
            logger.info(f"[ListagemDetalhada] Buscando pÃ¡gina {pagina_atual}...")
            
            # Fazer requisiÃ§Ã£o COM parÃ¢metro de pÃ¡gina
            resposta = listar_requisicoes_aplis(id_evento, periodo_ini, periodo_fim, "CodRequisicao", paginaAtual=pagina_atual)
            
            if resposta.get("dat", {}).get("sucesso") != 1:
                if pagina_atual == 1:
                    # Erro na primeira pÃ¡gina - problema real
                    logger.warning(f"[ListagemDetalhada] Falha ao obter lista primÃ¡ria: {resposta}")
                    return resposta
                else:
                    # Erro em pÃ¡gina posterior - parar a paginaÃ§Ã£o
                    logger.info(f"[ListagemDetalhada] Finalizando paginaÃ§Ã£o (erro na pÃ¡gina {pagina_atual})")
                    break
            
            dados_resposta = resposta.get("dat", {})
            lista_pagina = dados_resposta.get("lista", [])
            
            if not lista_pagina:
                logger.info(f"[ListagemDetalhada] PÃ¡gina {pagina_atual} vazia - finalizando paginaÃ§Ã£o")
                break
            
            logger.info(f"[ListagemDetalhada] PÃ¡gina {pagina_atual}: {len(lista_pagina)} requisiÃ§Ãµes")
            lista_requisicoes_total.extend(lista_pagina)
            
            # Verificar se hÃ¡ mais pÃ¡ginas
            qtd_paginas = dados_resposta.get("qtdPaginas", 1)
            registros_totais = dados_resposta.get("registros", len(lista_requisicoes_total))
            logger.debug(f"[ListagemDetalhada] Total de pÃ¡ginas: {qtd_paginas}, registros: {registros_totais}, pÃ¡gina atual: {pagina_atual}")
            
            if pagina_atual >= qtd_paginas:
                logger.info(f"[ListagemDetalhada] Todas as {qtd_paginas} pÃ¡ginas foram obtidas ({registros_totais} registros)")
                break
            
            pagina_atual += 1
        
        logger.info(f"[ListagemDetalhada] âœ… TOTAL de requisiÃ§Ãµes coletadas: {len(lista_requisicoes_total)}")
        
        if not enriquecer or len(lista_requisicoes_total) == 0:
            logger.info(f"[ListagemDetalhada] Retornando dados bÃ¡sicos (sem enriquecimento)")
            return {
                "dat": {
                    "sucesso": 1,
                    "lista": lista_requisicoes_total,
                    "total": len(lista_requisicoes_total),
                    "modo": "basico"
                }
            }
        
        # PASSO 2: Enriquecer dados complementares para cada requisiÃ§Ã£o
        logger.info(f"[ListagemDetalhada] Iniciando enriquecimento de dados para {len(lista_requisicoes_total)} requisiÃ§Ãµes")
        
        requisicoes_enriquecidas = []
        
        for idx, req in enumerate(lista_requisicoes_total, 1):
            try:
                cod_requisicao = req.get("CodRequisicao")
                logger.debug(f"[ListagemDetalhada] [{idx}/{len(lista_requisicoes_total)}] Enriquecendo: {cod_requisicao}")

                # ðŸ†• TENTAR BUSCAR DADOS COMPLEMENTARES DO requisicaoResultado
                dados_resultado = None
                try:
                    dat_resultado = {"codRequisicao": cod_requisicao}
                    resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

                    if resposta_resultado.get("dat", {}).get("sucesso") == 1:
                        dados_resultado = resposta_resultado.get("dat", {})
                        logger.debug(f"[ListagemDetalhada] âœ… Dados complementares obtidos para {cod_requisicao}")
                except Exception as e:
                    logger.debug(f"[ListagemDetalhada] requisicaoResultado nÃ£o disponÃ­vel para {cod_requisicao}: {str(e)}")

                # Extrair nomes do requisicaoResultado (se disponÃ­vel)
                nome_convenio = None
                nome_local_origem = None

                if dados_resultado:
                    # ConvÃªnio do resultado
                    if dados_resultado.get("paciente", {}).get("convenio"):
                        nome_convenio = dados_resultado["paciente"]["convenio"]

                    # Local de origem do resultado
                    if dados_resultado.get("localOrigem", {}).get("nome"):
                        nome_local_origem = dados_resultado["localOrigem"]["nome"]

                # Fallback para CSV se nÃ£o veio do resultado
                if not nome_convenio and req.get("IdConvenio"):
                    nome_convenio = _buscar_convenio_nome(req.get("IdConvenio"))

                if not nome_local_origem and req.get("IdLocalOrigem"):
                    nome_local_origem = _buscar_instituicao_nome(req.get("IdLocalOrigem"))
                

                # Dados primÃ¡rios (jÃ¡ vieram do requisicaoListar)
                req_enriquecida = {
                    # ===== DADOS PRIMÃRIOS (da busca inicial) =====
                    "dados_primarios": {
                        "codRequisicao": req.get("CodRequisicao"),
                        "idRequisicao": req.get("IdRequisicao"),
                        "dtaColeta": req.get("DtaColeta") or req.get("DtaPrevista"),
                        "numGuia": req.get("NumGuiaConvenio") or req.get("NumExterno"),
                        "dadosClinicos": req.get("IndicacaoClinica") or req.get("NomExame")
                    },
                    # ===== DADOS DO PACIENTE (primÃ¡rios) =====
                    "paciente": {
                        "idPaciente": req.get("CodPaciente"),
                        "nome": req.get("NomPaciente"),
                        "cpf": req.get("CPF"),  # PRINCIPAL: CPF vem do requisicaoListar
                        # Dados complementares (preenchidos por OCR ou manualmente)
                        "dtaNasc": None,
                        "sexo": None,
                        "rg": None,
                        "telCelular": None,
                        "endereco": {
                            "cep": None,
                            "logradouro": None,
                            "numEndereco": None,
                            "complemento": None,
                            "bairro": None,
                            "cidade": None,
                            "uf": None
                        }
                    },
                    # ===== DADOS COMPLEMENTARES (enriquecimento) =====
                    "dados_complementares": {
                        "idConvenio": req.get("IdConvenio"),
                        "idLocalOrigem": req.get("IdLocalOrigem"),
                        "idFontePagadora": req.get("IdFontePagadora"),
                        "idMedico": req.get("CodMedico")
                    },
                    "medico": {
                        "idMedico": req.get("CodMedico"),
                        "crm": req.get("CRM"),
                        "uf": req.get("CRMUF"),
                        "nome": None  # Pode ser preenchido por busca complementar
                    },
                    "convenio": {
                        "id": req.get("IdConvenio"),  # âœ… ID do convÃªnio
                        "nome": nome_convenio
                    },
                    "fontePagadora": {
                        "id": req.get("IdFontePagadora"),  # âœ… ID da fonte pagadora
                        "nome": None  # NÃ£o disponÃ­vel na API apLIS
                    },
                    "localOrigem": {
                        "id": req.get("IdLocalOrigem"),  # âœ… ID do local de origem
                        "nome": nome_local_origem
                    },
                    # Metadata
                    "origem": "requisicaoListar + requisicaoResultado",
                    "enriquecido": True
                }
                
                requisicoes_enriquecidas.append(req_enriquecida)
                
            except Exception as e:
                logger.error(f"[ListagemDetalhada] Erro ao enriquecer requisiÃ§Ã£o {cod_requisicao}: {str(e)}")
                # Ainda assim adiciona com dados bÃ¡sicos
                requisicoes_enriquecidas.append({
                    "codRequisicao": req.get("CodRequisicao"),
                    "paciente": {"nome": req.get("NomPaciente"), "cpf": req.get("CPF")},
                    "erro_enriquecimento": str(e)
                })
        
        logger.info(f"[ListagemDetalhada] âœ… Enriquecimento concluÃ­do: {len(requisicoes_enriquecidas)} requisiÃ§Ãµes")
        
        # Retornar resposta com dados enriquecidos
        return {
            "dat": {
                "sucesso": 1,
                "lista": requisicoes_enriquecidas,
                "total": len(requisicoes_enriquecidas),
                "modo": "detalhado_enriquecido",
                "avisos": [
                    "Dados do paciente (dtaNasc, sexo, rg, endereÃ§o) vÃªm do OCR ou devem ser preenchidos manualmente",
                    "Dados primÃ¡rios garantidos: codRequisicao, CPF, nome do paciente, data da coleta",
                    f"Total de {len(requisicoes_enriquecidas)} requisiÃ§Ãµes foram consultadas (TODAS as pÃ¡ginas)"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"[ListagemDetalhada] Erro geral: {str(e)}")
        import traceback
        logger.error(f"[ListagemDetalhada] Traceback: {traceback.format_exc()}")
        return {
            "dat": {
                "sucesso": 0,
                "erro": str(e),
                "modo": "detalhado_enriquecido"
            }
        }


@app.route('/api/requisicoes/listar', methods=['POST'])
def listar_requisicoes():
    """
    Lista requisiÃ§Ãµes do apLIS com dados PRIMÃRIOS e COMPLEMENTARES
    
    Esta funÃ§Ã£o integra duas metodologias:
    1. PRIMÃRIA: Dados bÃ¡sicos e importantes (requisiÃ§Ã£o, CPF, paciente)
    2. COMPLEMENTAR: InformaÃ§Ãµes adicionais (mÃ©dico, convÃªnio, local origem, etc)
    
    Exemplo de requisiÃ§Ã£o:
    {
        "idEvento": "50",
        "periodoIni": "2026-01-15",
        "periodoFim": "2026-01-15",
        "enriquecer": true  # (opcional, padrÃ£o: true) - Se deve buscar dados complementares
    }
    
    Resposta:
    {
        "sucesso": 1,
        "dados": {
            "lista": [
                {
                    "dados_primarios": { ... },      // Dados crÃ­ticos: cod requisiÃ§Ã£o, CPF, etc
                    "paciente": { ... },               // Nome, CPF (vem do requisicaoListar)
                    "medico": { ... },                 // CRM, UF
                    "dados_complementares": { ... },  // IDs de convÃªnio, fonte pagadora, etc
                    "convenio": { ... },
                    "fontePagadora": { ... },
                    "localOrigem": { ... }
                }
            ],
            "total": 10,
            "modo": "detalhado_enriquecido"
        }
    }
    """
    try:
        dados = request.json
        
        id_evento = dados.get('idEvento')
        periodo_ini = dados.get('periodoIni')
        periodo_fim = dados.get('periodoFim')
        enriquecer = dados.get('enriquecer', True)  # PadrÃ£o: ativo
        
        if not all([id_evento, periodo_ini, periodo_fim]):
            return jsonify({
                "sucesso": 0,
                "erro": "Campos obrigatÃ³rios: idEvento, periodoIni, periodoFim"
            }), 400
        
        logger.info(f"[ListagemEndpoint] RequisiÃ§Ã£o com enriquecimento={'ativo' if enriquecer else 'inativo'}")
        
        # Usar funÃ§Ã£o integrada que combina primÃ¡rio + complementar
        resposta = listar_requisicoes_detalhadas(id_evento, periodo_ini, periodo_fim, enriquecer)
        
        return jsonify({
            "sucesso": 1 if resposta.get("dat", {}).get("sucesso") == 1 else 0,
            "dados": resposta.get("dat", {}),
            "mensagem": "Listagem obtida com sucesso (dados primÃ¡rios + complementares)" if resposta.get("dat", {}).get("sucesso") == 1 else "Erro ao listar"
        }), 200
        
    except Exception as e:
        logger.error(f"[ListagemEndpoint] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao listar requisiÃ§Ãµes: {str(e)}"
        }), 500


@app.route('/api/requisicao/<cod_requisicao>', methods=['GET'])
def buscar_requisicao(cod_requisicao):
    """
    âœ… INTEGRALIZADO: Busca dados COMPLETOS de uma requisiÃ§Ã£o
    
    AGORA INTEGRA:
    1. DADOS PRIMÃRIOS: CÃ³digo requisiÃ§Ã£o, CPF, nome paciente (via requisicaoListar)
    2. DADOS COMPLEMENTARES: MÃ©dico, convÃªnio, fonte pagadora, local origem (via enriquecimento)
    3. IMAGENS: Do S3 (AWS)
    4. DADOS OCR: Vazios atÃ© processamento (preenchidos depois)
    
    Retorna estrutura Ãºnica com todos os dados necessÃ¡rios para o frontend.
    """
    try:
        logger.info(f"[BuscarIntegrado] Iniciando busca para requisiÃ§Ã£o: {cod_requisicao}")

        # âœ… NOVA ESTRATÃ‰GIA: Busca DIRETA por cÃ³digo (SEM perÃ­odo especÃ­fico)
        # Isso permite encontrar requisiÃ§Ãµes mesmo em perÃ­odos antigos
        logger.info(f"[BuscarIntegrado] Tentando busca direta por cÃ³digo...")
        
        # PASSO 1: Busca direta usando cÃ³digo como filtro (SEM perÃ­odo)
        dat_direto = {
            "idEvento": "50",
            "codRequisicao": cod_requisicao
        }
        
        resposta_direta = fazer_requisicao_aplis("requisicaoListar", dat_direto)
        
        # Log detalhado da resposta para debug
        logger.info(f"[BuscarIntegrado] ==================== RESPOSTA APLIS ====================")
        logger.info(f"[BuscarIntegrado] [DEBUG] Resposta COMPLETA: {resposta_direta}")
        logger.info(f"[BuscarIntegrado] [DEBUG] Chaves da resposta: {list(resposta_direta.keys())}")
        logger.info(f"[BuscarIntegrado] [DEBUG] Resposta dat: {resposta_direta.get('dat', {})}")
        logger.info(f"[BuscarIntegrado] [DEBUG] Sucesso: {resposta_direta.get('dat', {}).get('sucesso')}")
        logger.info(f"[BuscarIntegrado] [DEBUG] Tamanho da lista: {len(resposta_direta.get('dat', {}).get('lista', []))}")
        logger.info(f"[BuscarIntegrado] [DEBUG] Erro: {resposta_direta.get('erro')}")
        logger.info(f"[BuscarIntegrado] [DEBUG] Texto: {resposta_direta.get('texto')}")
        logger.info(f"[BuscarIntegrado] ========================================================")
        
        # Verificar se encontrou direto
        if resposta_direta.get("dat", {}).get("sucesso") == 1:
            lista_direta = resposta_direta.get("dat", {}).get("lista", [])
            logger.info(f"[BuscarIntegrado] âœ… API retornou sucesso=1")
            logger.info(f"[BuscarIntegrado] ðŸ“Š Quantidade de requisiÃ§Ãµes retornadas: {len(lista_direta)}")
            
            if lista_direta and len(lista_direta) > 0:
                logger.info(f"[BuscarIntegrado] âœ… RequisiÃ§Ã£o encontrada por busca direta!")
                dados_aplis = lista_direta[0]
                
                # LOG DETALHADO DOS DADOS BRUTOS DO apLIS
                logger.info(f"[BuscarIntegrado] ðŸ“‹ DADOS BRUTOS DO apLIS:")
                logger.info(f"[BuscarIntegrado] ðŸ” TODAS AS CHAVES RETORNADAS: {list(dados_aplis.keys())}")
                logger.info(f"[BuscarIntegrado] ðŸ” DADOS COMPLETOS (JSON): {dados_aplis}")
                logger.info(f"[BuscarIntegrado]   - IdConvenio: {dados_aplis.get('IdConvenio')} (tipo: {type(dados_aplis.get('IdConvenio'))})")
                logger.info(f"[BuscarIntegrado]   - IdLocalOrigem: {dados_aplis.get('IdLocalOrigem')} (tipo: {type(dados_aplis.get('IdLocalOrigem'))})")
                logger.info(f"[BuscarIntegrado]   - IdFontePagadora: {dados_aplis.get('IdFontePagadora')} (tipo: {type(dados_aplis.get('IdFontePagadora'))})")
                logger.info(f"[BuscarIntegrado]   - NomeConvenio: {dados_aplis.get('NomeConvenio')}")
                logger.info(f"[BuscarIntegrado]   - NomeFontePagadora: {dados_aplis.get('NomeFontePagadora')}")
                logger.info(f"[BuscarIntegrado]   - NumGuiaConvenio: {dados_aplis.get('NumGuiaConvenio')}")
                logger.info(f"[BuscarIntegrado]   - NumExterno: {dados_aplis.get('NumExterno')}")
                
                # ðŸ†• BUSCAR VARIAÃ‡Ã•ES DO CAMPO (pode ter nome diferente)
                num_guia_variacoes = [
                    dados_aplis.get('NumGuiaConvenio'),
                    dados_aplis.get('NumExterno'),
                    dados_aplis.get('numGuiaConvenio'),
                    dados_aplis.get('numGuia'),
                    dados_aplis.get('GuiaConvenio'),
                    dados_aplis.get('NumGuia')
                ]
                logger.info(f"[BuscarIntegrado] ðŸŽ« VARIAÃ‡Ã•ES DE NumGuia encontradas: {[v for v in num_guia_variacoes if v]}")
                
                # PASSO 2: Buscar imagens no S3
                imagens = []
                s3_client = get_s3_client()

                if s3_client:
                    try:
                        prefixo_lab = cod_requisicao[:4] if len(cod_requisicao) >= 4 else '0040'
                        caminho_s3_base = f"lab/Arquivos/Foto/{prefixo_lab}/{cod_requisicao}"

                        logger.info(f"[BuscarIntegrado][S3] Buscando imagens em: {caminho_s3_base}")

                        response_s3 = s3_client.list_objects_v2(
                            Bucket=S3_BUCKET,
                            Prefix=caminho_s3_base
                        )

                        if 'Contents' in response_s3:
                            for obj in response_s3['Contents']:
                                key = obj['Key']
                                filename = key.split('/')[-1]

                                if not filename or not filename.startswith(cod_requisicao):
                                    continue

                                try:
                                    arquivo_local = os.path.join(TEMP_IMAGES_DIR, filename)

                                    if not os.path.exists(arquivo_local):
                                        logger.info(f"[BuscarIntegrado][S3] Baixando: {key}")
                                        s3_client.download_file(S3_BUCKET, key, arquivo_local)
                                    else:
                                        logger.debug(f"[BuscarIntegrado][S3] JÃ¡ em cache: {filename}")

                                    base_url = request.host_url.rstrip('/')
                                    url_local = f"{base_url}/api/imagem/{filename}"

                                    imagens.append({
                                        "nome": filename,
                                        "url": url_local,
                                        "tamanho": obj['Size'],
                                        "dataCadastro": obj['LastModified'].isoformat()
                                    })

                                except Exception as e:
                                    logger.error(f"[BuscarIntegrado][S3] Erro ao processar {filename}: {e}")

                            logger.info(f"[BuscarIntegrado][S3] âœ… Encontradas {len(imagens)} imagens")
                        else:
                            logger.info(f"[BuscarIntegrado][S3] Nenhuma imagem em {caminho_s3_base}")

                    except Exception as e:
                        logger.error(f"[BuscarIntegrado][S3] Erro ao buscar imagens: {str(e)}")
                else:
                    logger.warning("[BuscarIntegrado][S3] Cliente S3 nÃ£o disponÃ­vel")

                # PASSO 3: ðŸ†• BUSCAR DADOS DO requisicaoResultado (SEMPRE tentar, independente do status)
                # ESTRATÃ‰GIA: requisicaoListar Ã© PRIMÃRIO (rÃ¡pido, sem atraso)
                #             requisicaoResultado Ã© COMPLEMENTO (convÃªnio, local origem, etc.)
                dados_resultado = None
                status_exame = dados_aplis.get("StatusExame")  # 0=andamento, 1=concluÃ­do, 2=cancelado

                logger.info(f"[BuscarIntegrado] ðŸ“‹ Tentando buscar dados complementares do requisicaoResultado...")
                dat_resultado = {"codRequisicao": cod_requisicao}
                resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

                if resposta_resultado.get("dat", {}).get("sucesso") == 1:
                    dados_resultado = resposta_resultado.get("dat", {})
                    logger.info(f"[BuscarIntegrado] âœ… Dados complementares obtidos do requisicaoResultado!")
                    
                    # ðŸ†• LOG COMPLETO DO requisicaoResultado
                    logger.info(f"[BuscarIntegrado] ðŸ” CHAVES DO requisicaoResultado: {list(dados_resultado.keys())}")
                    if dados_resultado.get("requisicao"):
                        logger.info(f"[BuscarIntegrado] ðŸ” CHAVES DE requisicao: {list(dados_resultado['requisicao'].keys())}")
                        logger.info(f"[BuscarIntegrado] ðŸ” DADOS COMPLETOS DE requisicao: {dados_resultado['requisicao']}")

                    # Extrair localOrigem do resultado
                    if dados_resultado.get("localOrigem"):
                        local_origem_resultado = dados_resultado["localOrigem"]
                        logger.info(f"[BuscarIntegrado] ðŸ¥ Local de Origem: {local_origem_resultado.get('nome')}")

                    # Extrair convÃªnio do resultado
                    if dados_resultado.get("paciente", {}).get("convenio"):
                        convenio_resultado = dados_resultado["paciente"]["convenio"]
                        logger.info(f"[BuscarIntegrado] ðŸ’³ ConvÃªnio: {convenio_resultado}")
                    
                    # Extrair NumGuia do resultado (se disponÃ­vel) - BUSCAR EM VÃRIOS LUGARES
                    num_guia_resultado = None
                    
                    # Tentar vÃ¡rias localizaÃ§Ãµes possÃ­veis
                    if dados_resultado.get("requisicao"):
                        num_guia_resultado = (
                            dados_resultado["requisicao"].get("numGuia") or
                            dados_resultado["requisicao"].get("NumGuiaConvenio") or
                            dados_resultado["requisicao"].get("numGuiaConvenio") or
                            dados_resultado["requisicao"].get("GuiaConvenio") or
                            dados_resultado["requisicao"].get("NumExterno")
                        )
                    
                    if num_guia_resultado:
                        logger.info(f"[BuscarIntegrado] ðŸŽ« NumGuia do resultado: {num_guia_resultado}")
                        # Atualizar dados_aplis se estiver vazio
                        if not dados_aplis.get("NumGuiaConvenio"):
                            dados_aplis["NumGuiaConvenio"] = num_guia_resultado
                            logger.info(f"[BuscarIntegrado] âœ… NumGuia atualizado de requisicaoResultado")
                    else:
                        logger.warning(f"[BuscarIntegrado] âš ï¸ NumGuia nÃ£o encontrado em requisicaoResultado")
                else:
                    logger.warning(f"[BuscarIntegrado] âš ï¸ requisicaoResultado nÃ£o disponÃ­vel (StatusExame={status_exame})")
                    if status_exame == 0:
                        logger.info(f"[BuscarIntegrado] â„¹ï¸ RequisiÃ§Ã£o em andamento - dados complementares virÃ£o quando finalizar")

                # PASSO 3.5: ðŸ†• BUSCAR NumGuiaConvenio DIRETO DO BANCO (fallback se apLIS nÃ£o retornar)
                num_guia_banco = None
                if not dados_aplis.get("NumGuiaConvenio") and not dados_aplis.get("NumExterno"):
                    logger.info(f"[BuscarIntegrado] ðŸ” NumGuia vazio no apLIS, buscando no banco...")
                    try:
                        connection = pymysql.connect(**DB_CONFIG)
                        cursor = connection.cursor(pymysql.cursors.DictCursor)
                        
                        query = "SELECT NumGuiaConvenio, NumExterno FROM newdb.requisicao WHERE CodRequisicao = %s LIMIT 1"
                        logger.info(f"[BuscarIntegrado] ðŸ” Query SQL: {query} (CodRequisicao={cod_requisicao})")
                        cursor.execute(query, (cod_requisicao,))
                        resultado_guia = cursor.fetchone()
                        
                        logger.info(f"[BuscarIntegrado] ðŸ” Resultado SQL: {resultado_guia}")
                        
                        cursor.close()
                        connection.close()
                        
                        if resultado_guia:
                            num_guia_banco = resultado_guia.get("NumGuiaConvenio") or resultado_guia.get("NumExterno")
                            if num_guia_banco:
                                logger.info(f"[BuscarIntegrado] âœ… NumGuia encontrado no banco: {num_guia_banco}")
                                # Atualizar dados_aplis para usar depois
                                dados_aplis["NumGuiaConvenio"] = num_guia_banco
                            else:
                                logger.warning(f"[BuscarIntegrado] âš ï¸ NumGuia tambÃ©m estÃ¡ vazio no banco (NumGuiaConvenio={resultado_guia.get('NumGuiaConvenio')}, NumExterno={resultado_guia.get('NumExterno')})")
                        else:
                            logger.warning(f"[BuscarIntegrado] âš ï¸ RequisiÃ§Ã£o {cod_requisicao} nÃ£o encontrada no banco")
                    except Exception as e:
                        logger.error(f"[BuscarIntegrado] âŒ Erro ao buscar NumGuia no banco: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.info(f"[BuscarIntegrado] â„¹ï¸ NumGuia jÃ¡ existe no apLIS, nÃ£o buscando no banco")

                # PASSO 4: ðŸ†• BUSCAR DADOS COMPLETOS DO PACIENTE VIA API
                logger.info(f"[BuscarIntegrado] ðŸ“¡ Buscando dados completos do paciente via API...")
                dados_sistema_antigo = None
                cod_paciente = dados_aplis.get("CodPaciente")
                
                # Confiar no CodPaciente retornado pela API
                logger.info(f"[BuscarIntegrado] âœ… Usando CodPaciente da API: {cod_paciente}")

                # ðŸ”„ BUSCA HÃBRIDA: API primeiro, Banco SQL como fallback/complemento
                logger.info(f"[BuscarIntegrado] ðŸ”„ Iniciando busca hÃ­brida de dados do paciente...")
                
                # PRIORIDADE 1: Buscar via API (requisicaoResultado)
                dados_paciente_api = buscar_dados_paciente_via_api(cod_requisicao)
                
                # PRIORIDADE 2: Buscar no banco SQL (se necessÃ¡rio)
                dados_paciente_banco = None
                if cod_paciente:
                    dados_paciente_banco = buscar_dados_completos_paciente(cod_paciente)
                
                # ðŸ”€ MESCLAR dados: API tem prioridade, banco complementa o que falta
                dados_finais = {}
                origem_dados = []
                
                if dados_paciente_api:
                    logger.info(f"[BuscarIntegrado] âœ… Dados da API disponÃ­veis")
                    dados_finais.update(dados_paciente_api)
                    origem_dados.append("API")
                
                if dados_paciente_banco:
                    logger.info(f"[BuscarIntegrado] âœ… Dados do banco disponÃ­veis")
                    # Complementar apenas campos que estÃ£o vazios/None
                    for campo, valor in dados_paciente_banco.items():
                        if campo != "origem" and (not dados_finais.get(campo) or dados_finais.get(campo) is None):
                            dados_finais[campo] = valor
                    if "BANCO_SQL" not in origem_dados:
                        origem_dados.append("BANCO_SQL")
                
                if dados_finais:
                    logger.info(f"[BuscarIntegrado] âœ… Dados mesclados! Origem: {' + '.join(origem_dados)}")
                    
                    # Montar estrutura dados_sistema_antigo com dados mesclados
                    dados_sistema_antigo = {
                        "dtaNasc": dados_finais.get("DtaNascimento"),
                        "sexo": dados_finais.get("Sexo"),
                        "rg": dados_finais.get("RGNumero"),
                        "rgOrgao": dados_finais.get("RGOrgao"),
                        "rgUF": dados_finais.get("RGUF"),
                        "nomeMae": dados_finais.get("NomMae"),
                        "estadoCivil": dados_finais.get("EstadoCivil"),
                        "passaporte": dados_finais.get("Passaporte"),
                        "matriculaConvenio": dados_finais.get("MatConvenio"),
                        "validadeMatricula": dados_finais.get("ValidadeMatricula"),
                        "telCelular": dados_finais.get("TelCelular"),
                        "telFixo": dados_finais.get("TelFixo"),
                        "email": dados_finais.get("Email"),
                        "endereco": {
                            "cep": dados_finais.get("Cep"),
                            "logradouro": dados_finais.get("Logradouro"),
                            "numEndereco": dados_finais.get("NumEndereco"),
                            "complemento": dados_finais.get("Complemento"),
                            "bairro": dados_finais.get("Bairro"),
                            "cidade": dados_finais.get("Cidade"),
                            "uf": dados_finais.get("UF")
                        },
                        "_origem": origem_dados  # Metadado para debug
                    }
                    
                    # Atualizar dados principais se disponÃ­veis
                    if dados_finais.get("CPF"):
                        dados_aplis["CPF"] = dados_finais.get("CPF")
                    if dados_finais.get("NomPaciente"):
                        dados_aplis["NomPaciente"] = dados_finais.get("NomPaciente")
                else:
                    logger.warning(f"[BuscarIntegrado] âš ï¸ Dados do paciente nÃ£o encontrados (nem API nem banco)")
                    dados_sistema_antigo = None

                # PASSO 4: ðŸ†• BUSCAR IDs DO BANCO DE DADOS
                # IMPORTANTE: A API requisicaoListar NÃƒO retorna IdConvenio, IdFontePagadora, IdLocalOrigem
                # quando StatusExame = 0 (Aguarda AdmissÃ£o). Esses campos sÃ³ aparecem apÃ³s a admissÃ£o ser salva.
                # Por isso, SEMPRE buscamos no banco MySQL, que Ã© a fonte de verdade para esses IDs.
                logger.info(f"[BuscarIntegrado] ðŸ—„ï¸ Buscando IDs do banco de dados MySQL (fonte principal)...")
                ids_banco = buscar_ids_banco(cod_requisicao)

                # Atualizar dados_aplis com os IDs do banco
                if ids_banco.get("IdConvenio") is not None:
                    dados_aplis["IdConvenio"] = ids_banco["IdConvenio"]
                    logger.info(f"[BuscarIntegrado] âœ… IdConvenio do BANCO: {ids_banco['IdConvenio']}")
                else:
                    logger.warning(f"[BuscarIntegrado] âš ï¸ IdConvenio NÃƒO encontrado no banco (requisiÃ§Ã£o sem convÃªnio salvo)")

                if ids_banco.get("IdFontePagadora") is not None:
                    dados_aplis["IdFontePagadora"] = ids_banco["IdFontePagadora"]
                    logger.info(f"[BuscarIntegrado] âœ… IdFontePagadora do BANCO: {ids_banco['IdFontePagadora']}")
                else:
                    logger.warning(f"[BuscarIntegrado] âš ï¸ IdFontePagadora NÃƒO encontrada no banco (requisiÃ§Ã£o sem fonte pagadora salva)")

                if ids_banco.get("IdLocalOrigem") is not None:
                    dados_aplis["IdLocalOrigem"] = ids_banco["IdLocalOrigem"]
                    logger.info(f"[BuscarIntegrado] âœ… IdLocalOrigem do BANCO: {ids_banco['IdLocalOrigem']}")
                else:
                    logger.warning(f"[BuscarIntegrado] âš ï¸ IdLocalOrigem NÃƒO encontrado no banco (requisiÃ§Ã£o sem local origem salvo)")

                # PASSO 5: ðŸ†• ENRIQUECER COM DADOS DOS CSVs
                logger.info(f"[BuscarIntegrado] ðŸ” Enriquecendo com dados dos CSVs...")

                # Buscar nome do mÃ©dico no CSV
                nome_medico = None
                if dados_aplis.get("CRM") and dados_aplis.get("CRMUF"):
                    medico_csv = buscar_medico_por_crm(dados_aplis.get("CRM"), dados_aplis.get("CRMUF"))
                    if medico_csv:
                        nome_medico = medico_csv['nome']
                        logger.info(f"[BuscarIntegrado] âœ… MÃ©dico encontrado no CSV: {nome_medico}")
                    else:
                        logger.warning(f"[BuscarIntegrado] âš ï¸ MÃ©dico CRM {dados_aplis.get('CRM')}/{dados_aplis.get('CRMUF')} nÃ£o encontrado no CSV")

                # Buscar nome do convÃªnio
                # PRIORIDADE 1: Se veio do requisicaoResultado, usar direto
                # PRIORIDADE 2: Buscar no CSV usando IdConvenio (agora do banco!)
                nome_convenio = None
                id_convenio = dados_aplis.get("IdConvenio")  # Agora vem do banco!
                origem_convenio = None

                if dados_resultado and dados_resultado.get("paciente", {}).get("convenio"):
                    nome_convenio = dados_resultado["paciente"]["convenio"]
                    origem_convenio = "apLIS:requisicaoResultado"
                    logger.info(f"[BuscarIntegrado] âœ… ðŸ’³ CONVÃŠNIO do apLIS (requisicaoResultado): '{nome_convenio}'")
                else:
                    if id_convenio:
                        nome_convenio = _buscar_convenio_nome(id_convenio)
                        origem_convenio = f"CSV via IdConvenio={id_convenio} (do banco MySQL)"
                        logger.info(f"[BuscarIntegrado] ðŸ” ðŸ’³ CONVÃŠNIO do CSV (IdConvenio {id_convenio} do BANCO): '{nome_convenio}'")
                    else:
                        nome_convenio = "NÃ£o informado"
                        origem_convenio = "FALLBACK - IdConvenio nÃ£o disponÃ­vel no banco"
                        logger.warning(f"[BuscarIntegrado] âš ï¸ ðŸ’³ CONVÃŠNIO: IdConvenio nÃ£o disponÃ­vel - usando fallback")
                
                logger.info(f"[BuscarIntegrado] ðŸ“Š ORIGEM DO CONVÃŠNIO: {origem_convenio or 'NÃƒO ENCONTRADO'}")

                # Buscar nome da fonte pagadora no CSV de instituiÃ§Ãµes
                # IMPORTANTE: requisicaoListar NÃƒO retorna NomeFontePagadora, apenas IdFontePagadora
                nome_fonte_pagadora = None
                id_fonte_pagadora = dados_aplis.get("IdFontePagadora")
                origem_fonte = None
                
                if id_fonte_pagadora:
                    nome_fonte_pagadora = _buscar_instituicao_nome(id_fonte_pagadora)
                    origem_fonte = f"CSV via IdFontePagadora={id_fonte_pagadora} (do banco MySQL)"
                    logger.info(f"[BuscarIntegrado] ðŸ” ðŸ’° FONTE PAGADORA do CSV (IdFontePagadora {id_fonte_pagadora} do BANCO): '{nome_fonte_pagadora}'")
                else:
                    nome_fonte_pagadora = "NÃ£o informado"
                    origem_fonte = "FALLBACK - IdFontePagadora nÃ£o disponÃ­vel no banco"
                    logger.warning(f"[BuscarIntegrado] âš ï¸ ðŸ’° FONTE PAGADORA: IdFontePagadora nÃ£o disponÃ­vel - usando fallback")
                
                logger.info(f"[BuscarIntegrado] ðŸ“Š ORIGEM DA FONTE PAGADORA: {origem_fonte or 'NÃƒO ENCONTRADO'}")

                # Buscar nome do local de origem
                # PRIORIDADE 1: Se veio do requisicaoResultado, usar direto
                # PRIORIDADE 2: Buscar no CSV usando IdLocalOrigem
                nome_local_origem = None
                origem_local = None
                
                if dados_resultado and dados_resultado.get("localOrigem"):
                    nome_local_origem = dados_resultado["localOrigem"].get("nome")
                    origem_local = "apLIS:requisicaoResultado"
                    logger.info(f"[BuscarIntegrado] âœ… ðŸ¥ LOCAL DE ORIGEM do apLIS (requisicaoResultado): '{nome_local_origem}'")
                else:
                    id_local_origem = dados_aplis.get("IdLocalOrigem")
                    if id_local_origem:
                        nome_local_origem = _buscar_instituicao_nome(id_local_origem)
                        origem_local = f"CSV via IdLocalOrigem={id_local_origem} (do banco MySQL)"
                        logger.info(f"[BuscarIntegrado] ðŸ” ðŸ¥ LOCAL DE ORIGEM do CSV (IdLocalOrigem {id_local_origem} do BANCO): '{nome_local_origem}'")
                    else:
                        nome_local_origem = "NÃ£o informado"
                        origem_local = "FALLBACK - IdLocalOrigem nÃ£o disponÃ­vel no banco"
                        logger.warning(f"[BuscarIntegrado] âš ï¸ ðŸ¥ LOCAL DE ORIGEM: IdLocalOrigem nÃ£o disponÃ­vel - usando fallback")
                
                logger.info(f"[BuscarIntegrado] ðŸ“Š ORIGEM DO LOCAL DE ORIGEM: {origem_local or 'NÃƒO ENCONTRADO'}")

                # PASSO 4.5: VALIDAR CPF COM RECEITA FEDERAL
                logger.info(f"[BuscarIntegrado] ðŸ” Validando CPF com Receita Federal...")
                validacao_cpf = validar_e_corrigir_dados_cpf(dados_aplis, dados_sistema_antigo)

                # Usar dados validados da Receita Federal (se disponÃ­vel)
                nome_paciente_final = validacao_cpf["dados"]["nome"] or dados_aplis.get("NomPaciente")
                cpf_final = validacao_cpf["dados"]["cpf"] or dados_aplis.get("CPF")
                data_nasc_final = validacao_cpf["dados"]["dtaNasc"]

                # Se data de nascimento nÃ£o veio da Receita, usar do sistema antigo
                if not data_nasc_final and dados_sistema_antigo:
                    data_nasc_final = dados_sistema_antigo.get("dtaNasc")

                # ðŸ†• PASSO 4.5.5: BUSCAR NO SUPABASE (HISTÃ“RICO)
                # Se data de nascimento ainda nÃ£o foi encontrada, buscar no histÃ³rico do Supabase
                # (pode ter sido calculada a partir da idade em processamento anterior)
                if not data_nasc_final and SUPABASE_ENABLED:
                    try:
                        logger.info(f"[BuscarIntegrado] ðŸ” Buscando data de nascimento no histÃ³rico Supabase...")
                        resultado_supabase = supabase_manager.buscar_requisicao(cod_requisicao)

                        if resultado_supabase.get('sucesso') == 1:
                            dados_supabase = resultado_supabase.get('dados', {})
                            data_nasc_supabase = dados_supabase.get('data_nascimento')

                            if data_nasc_supabase:
                                # Converter de YYYY-MM-DD para DD/MM/YYYY (formato esperado)
                                try:
                                    data_obj = datetime.strptime(data_nasc_supabase, '%Y-%m-%d')
                                    data_nasc_final = data_obj.strftime('%d/%m/%Y')
                                    logger.info(f"[BuscarIntegrado] âœ… Data de nascimento do Supabase: {data_nasc_final}")
                                except:
                                    data_nasc_final = data_nasc_supabase
                                    logger.info(f"[BuscarIntegrado] âœ… Data de nascimento do Supabase (formato direto): {data_nasc_final}")
                        else:
                            logger.debug(f"[BuscarIntegrado] RequisiÃ§Ã£o nÃ£o encontrada no Supabase")
                    except Exception as e:
                        logger.warning(f"[BuscarIntegrado] Erro ao buscar no Supabase: {e}")

                # PASSO 4.6: ðŸ†• BUSCAR REQUISIÃ‡ÃƒO CORRESPONDENTE (085 â†” 0200)
                # Se esta requisiÃ§Ã£o comeÃ§a com 085 ou 0200, buscar dados do paciente da correspondente
                logger.info(f"[BuscarIntegrado] Verificando requisicao correspondente (085 <-> 0200)...")
                logger.info(f"[BuscarIntegrado] Codigo da requisicao para sincronizacao: {cod_requisicao}")

                # ESTRATÃ‰GIA: Tentar banco primeiro (mais rÃ¡pido), depois apLIS (fallback)
                req_correspondente = buscar_requisicao_correspondente(cod_requisicao)

                if not req_correspondente:
                    logger.info(f"[BuscarIntegrado] âš ï¸ NÃ£o encontrada no banco, tentando buscar do apLIS...")
                    req_correspondente = buscar_requisicao_correspondente_aplis(cod_requisicao)

                logger.info(f"[BuscarIntegrado] Resultado da busca correspondente: {req_correspondente is not None}")

                if req_correspondente:
                    # PRIORIDADE: Dados da requisiÃ§Ã£o correspondente > Sistema Antigo
                    # Isso garante que 085 e 0200 tenham EXATAMENTE os mesmos dados de paciente
                    logger.info(f"[BuscarIntegrado] ðŸ”„ Sincronizando dados do paciente com requisiÃ§Ã£o correspondente...")

                    # Se nÃ£o tem nome ou CPF, usar da correspondente
                    if not nome_paciente_final and req_correspondente.get("NomePaciente"):
                        nome_paciente_final = req_correspondente["NomePaciente"]
                        logger.info(f"[BuscarIntegrado] âœ… Nome do paciente sincronizado: {nome_paciente_final}")

                    if not cpf_final and req_correspondente.get("CPF"):
                        cpf_final = req_correspondente["CPF"]
                        logger.info(f"[BuscarIntegrado] âœ… CPF sincronizado: {cpf_final}")

                    if not data_nasc_final and req_correspondente.get("DtaNasc"):
                        data_nasc_final = req_correspondente["DtaNasc"]
                        logger.info(f"[BuscarIntegrado] âœ… Data nascimento sincronizada: {data_nasc_final}")

                    # Atualizar dados_sistema_antigo com os dados da correspondente
                    if not dados_sistema_antigo:
                        dados_sistema_antigo = {}

                    # Sincronizar TODOS os campos do paciente
                    if req_correspondente.get("Sexo"):
                        dados_sistema_antigo["sexo"] = req_correspondente["Sexo"]
                    if req_correspondente.get("RG"):
                        dados_sistema_antigo["rg"] = req_correspondente["RG"]
                    if req_correspondente.get("RGOrgao"):
                        dados_sistema_antigo["rgOrgao"] = req_correspondente["RGOrgao"]
                    if req_correspondente.get("RGUF"):
                        dados_sistema_antigo["rgUF"] = req_correspondente["RGUF"]
                    if req_correspondente.get("TelCelular"):
                        dados_sistema_antigo["telCelular"] = req_correspondente["TelCelular"]
                    if req_correspondente.get("TelFixo"):
                        dados_sistema_antigo["telFixo"] = req_correspondente["TelFixo"]
                    if req_correspondente.get("NomMae"):
                        dados_sistema_antigo["nomeMae"] = req_correspondente["NomMae"]
                    if req_correspondente.get("EstadoCivil"):
                        dados_sistema_antigo["estadoCivil"] = req_correspondente["EstadoCivil"]
                    if req_correspondente.get("Passaporte"):
                        dados_sistema_antigo["passaporte"] = req_correspondente["Passaporte"]
                    if req_correspondente.get("MatConvenio"):
                        dados_sistema_antigo["matriculaConvenio"] = req_correspondente["MatConvenio"]
                    if req_correspondente.get("ValidadeMatricula"):
                        dados_sistema_antigo["validadeMatricula"] = req_correspondente["ValidadeMatricula"]

                    # EndereÃ§o completo
                    dados_sistema_antigo["endereco"] = {
                        "cep": req_correspondente.get("CEP"),
                        "logradouro": req_correspondente.get("Logradouro"),
                        "numEndereco": req_correspondente.get("NumEndereco"),
                        "complemento": req_correspondente.get("Complemento"),
                        "bairro": req_correspondente.get("Bairro"),
                        "cidade": req_correspondente.get("Cidade"),
                        "uf": req_correspondente.get("UF")
                    }

                    logger.info(f"[BuscarIntegrado] âœ… Dados do paciente sincronizados com sucesso!")
                    logger.info(f"[BuscarIntegrado]    Sincronizados: RG, telefones, mae, estado civil, endereco completo, matricula convenio")

                # PASSO 5: Montar resposta ENRIQUECIDA com dados primÃ¡rios + complementares + sistema antigo + CSVs
                id_medico = dados_aplis.get("CodMedico")
                id_local_origem = dados_aplis.get("IdLocalOrigem")  # Definir aqui para uso posterior

                logger.debug(f"[BuscarIntegrado] IDs da requisiÃ§Ã£o: convenio={id_convenio}, fonte={id_fonte_pagadora}, local={id_local_origem}, medico={id_medico}")
                logger.debug(f"[BuscarIntegrado] Nomes obtidos: convenio={nome_convenio}, fonte={nome_fonte_pagadora}, local={nome_local_origem}")
                
                # ðŸ”´ LOG CRÃTICO: DEBUGAR RESPOSTA FINAL
                logger.info(f"")
                logger.info(f"[BuscarIntegrado] {'='*80}")
                logger.info(f"[BuscarIntegrado] ðŸ” DEBUG - RESPOSTA QUE SERÃ ENVIADA AO FRONTEND")
                logger.info(f"[BuscarIntegrado] {'='*80}")
                logger.info(f"[BuscarIntegrado] ðŸ’³ CONVÃŠNIO:")
                logger.info(f"[BuscarIntegrado]    ID: {id_convenio}")
                logger.info(f"[BuscarIntegrado]    NOME: '{nome_convenio}'")
                logger.info(f"[BuscarIntegrado] ðŸ’° FONTE PAGADORA:")
                logger.info(f"[BuscarIntegrado]    ID: {id_fonte_pagadora}")
                logger.info(f"[BuscarIntegrado]    NOME: '{nome_fonte_pagadora}'")
                logger.info(f"[BuscarIntegrado] ðŸ¥ LOCAL DE ORIGEM:")
                logger.info(f"[BuscarIntegrado]    ID: {id_local_origem}")
                logger.info(f"[BuscarIntegrado]    NOME: '{nome_local_origem}'")
                logger.info(f"[BuscarIntegrado] {'='*80}")
                logger.info(f"")
                
                # LOG: Verificar valor do numGuia antes de montar resposta
                num_guia_final = dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno") or (dados_sistema_antigo.get("numGuia") if dados_sistema_antigo else None)
                logger.info(f"[BuscarIntegrado] ðŸŽ« NumGuia FINAL que serÃ¡ enviado: {num_guia_final}")
                logger.info(f"[BuscarIntegrado]    - NumGuiaConvenio (apLIS): {dados_aplis.get('NumGuiaConvenio')}")
                logger.info(f"[BuscarIntegrado]    - NumExterno (apLIS): {dados_aplis.get('NumExterno')}")
                logger.info(f"[BuscarIntegrado]    - numGuia (banco antigo): {dados_sistema_antigo.get('numGuia') if dados_sistema_antigo else 'N/A'}")
                
                resultado = {
                    "sucesso": 1,
                    # ===== DADOS PRIMÃRIOS (da busca direta) =====
                    "dados_primarios": {
                        "codRequisicao": dados_aplis.get("CodRequisicao"),
                        "idRequisicao": dados_aplis.get("IdRequisicao"),
                        "dtaColeta": dados_aplis.get("DtaColeta") or dados_aplis.get("DtaPrevista"),
                        "numGuia": dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno"),
                        "dadosClinicos": dados_aplis.get("IndicacaoClinica") or dados_aplis.get("NomExame")
                    },
                    # ===== DADOS DO PACIENTE (CPF Ã© principal) =====
                    "paciente": {
                        "idPaciente": dados_aplis.get("CodPaciente"),
                        "nome": nome_paciente_final,  # âœ… PRIORIDADE: Receita Federal â†’ apLIS
                        "cpf": cpf_final,  # âœ… PRIORIDADE: Receita Federal â†’ apLIS

                        # ðŸ†• Dados do SISTEMA ANTIGO (se disponÃ­vel) ou Receita Federal ou None (para OCR preencher)
                        "dtaNasc": data_nasc_final,  # âœ… PRIORIDADE: Receita Federal â†’ Sistema Antigo
                        "sexo": dados_sistema_antigo.get("sexo") if dados_sistema_antigo else None,
                        "rg": dados_sistema_antigo.get("rg") if dados_sistema_antigo else None,
                        "rgOrgao": dados_sistema_antigo.get("rgOrgao") if dados_sistema_antigo else None,
                        "rgUF": dados_sistema_antigo.get("rgUF") if dados_sistema_antigo else None,
                        "nomeMae": dados_sistema_antigo.get("nomeMae") if dados_sistema_antigo else None,
                        "estadoCivil": dados_sistema_antigo.get("estadoCivil") if dados_sistema_antigo else None,
                        "passaporte": dados_sistema_antigo.get("passaporte") if dados_sistema_antigo else None,
                        "matriculaConvenio": dados_sistema_antigo.get("matriculaConvenio") if dados_sistema_antigo else None,
                        "validadeMatricula": dados_sistema_antigo.get("validadeMatricula") if dados_sistema_antigo else None,
                        "numGuia": dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno") or (dados_sistema_antigo.get("numGuia") if dados_sistema_antigo else None),
                        "telCelular": dados_sistema_antigo.get("telCelular") if dados_sistema_antigo else None,
                        "telFixo": dados_sistema_antigo.get("telFixo") if dados_sistema_antigo else None,
                        "email": dados_sistema_antigo.get("email") if dados_sistema_antigo else None,
                        "endereco": dados_sistema_antigo.get("endereco", {}) if dados_sistema_antigo else {
                            "cep": None,
                            "logradouro": None,
                            "numEndereco": None,
                            "complemento": None,
                            "bairro": None,
                            "cidade": None,
                            "uf": None
                        }
                    },
                    # ===== DADOS COMPLEMENTARES (enriquecimento) =====
                    "dados_complementares": {
                        "idConvenio": id_convenio,
                        "idLocalOrigem": id_local_origem,
                        "idFontePagadora": id_fonte_pagadora,
                        "idMedico": id_medico
                    },
                    # ===== DADOS DO MÃ‰DICO (enriquecido com CSV) =====
                    "medico": {
                        "idMedico": id_medico,
                        "crm": dados_aplis.get("CRM"),
                        "uf": dados_aplis.get("CRMUF"),
                        "nome": nome_medico  # âœ… Enriquecido do CSV
                    },
                    # ===== INFORMAÃ‡Ã•ES DE ORIGEM (enriquecidas com CSV) =====
                    "convenio": {
                        "id": id_convenio,  # âœ… ID do convÃªnio
                        "nome": nome_convenio  # âœ… Vem do CSV via _buscar_convenio_nome()
                    },
                    "fontePagadora": {
                        "id": id_fonte_pagadora,  # âœ… ID da fonte pagadora
                        "nome": nome_fonte_pagadora  # âœ… Vem do CSV de instituiÃ§Ãµes via _buscar_instituicao_nome()
                    },
                    "localOrigem": {
                        "id": id_local_origem,  # âœ… ID do local de origem
                        "nome": nome_local_origem  # âœ… Vem do CSV de instituiÃ§Ãµes via _buscar_instituicao_nome()
                    },
                    # ===== IMAGENS =====
                    "imagens": imagens,
                    "totalImagens": len(imagens),
                    # ===== COMPATIBILIDADE COM FRONTEND =====
                    "requisicao": {
                        "codRequisicao": dados_aplis.get("CodRequisicao"),
                        "idRequisicao": dados_aplis.get("IdRequisicao"),
                        "dtaColeta": dados_aplis.get("DtaColeta") or dados_aplis.get("DtaPrevista"),
                        "numGuia": dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno"),
                        "dadosClinicos": dados_aplis.get("IndicacaoClinica") or dados_aplis.get("NomExame"),
                        "idConvenio": id_convenio,  # âœ… Com default
                        "idLocalOrigem": id_local_origem,  # âœ… Com default
                        "idFontePagadora": id_fonte_pagadora,  # âœ… Com default
                        "idMedico": id_medico  # âœ… Com default
                    },
                    # ===== METADATA =====
                    "origem": "busca_direta_por_codigo_enriquecida",
                    "statusIntegracao": "completo_dois_sistemas",
                    "avisos": [
                        f"âœ… Sistema NOVO: codRequisicao, CPF, nome (tempo real - mesmo dia)",
                        f"âœ… Sistema NOVO: mÃ©dico, convÃªnio, local origem, fonte pagadora",
                        f"{'âœ… Sistema ANTIGO: dtaNasc, sexo, RG, telefone, endereÃ§o completo' if dados_sistema_antigo else 'âš ï¸ Sistema ANTIGO: Dados nÃ£o encontrados (paciente pode ser novo ou ter 1 dia de atraso)'}",
                        f"{'âœ… RECEITA FEDERAL: Dados validados e corrigidos' if validacao_cpf.get('dados_corrigidos') else 'âœ… RECEITA FEDERAL: Dados conferem' if validacao_cpf.get('fonte_dados') == 'receita_federal' else 'âš ï¸ RECEITA FEDERAL: ValidaÃ§Ã£o nÃ£o disponÃ­vel'}",
                        f"ðŸ“‹ OCR: Pode complementar/substituir dados se houver imagens"
                    ],
                    "sistemas_utilizados": {
                        "sistema_novo": "requisicaoListar (tempo real)",
                        "sistema_antigo": "admissaoListar (dados completos)" if dados_sistema_antigo else "nÃ£o consultado",
                        "sistema_antigo_sucesso": dados_sistema_antigo is not None,
                        "receita_federal": validacao_cpf.get("fonte_dados") == "receita_federal",
                        "receita_federal_corrigiu": validacao_cpf.get("dados_corrigidos", False)
                    },
                    "validacao_cpf": {
                        "fonte_dados": validacao_cpf.get("fonte_dados"),
                        "dados_corrigidos": validacao_cpf.get("dados_corrigidos", False),
                        "divergencias": validacao_cpf.get("divergencias"),
                        "situacao_cadastral": validacao_cpf.get("situacao_cadastral")
                    },
                    # ===== SINCRONIZAÃ‡ÃƒO 0085 â†” 0200 =====
                    "sincronizacao": {
                        "sincronizado": req_correspondente is not None,
                        "codigo_correspondente": req_correspondente.get("CodRequisicao") if req_correspondente else None,
                        "tipo_sincronizacao": "0085 <-> 0200" if req_correspondente else None,
                        "campos_sincronizados": [
                            "nome", "cpf", "dtaNasc", "sexo", "rg", "rgOrgao", "rgUF",
                            "nomeMae", "estadoCivil", "passaporte", "matriculaConvenio",
                            "validadeMatricula", "telCelular", "telFixo", "endereco completo"
                        ] if req_correspondente else []
                    }
                }

                logger.info(f"[BuscarIntegrado] [SUCESSO] {cod_requisicao} ({len(imagens)} imagens)")
                return jsonify(resultado), 200
            else:
                logger.warning(f"[BuscarIntegrado] [AVISO] Busca direta retornou lista vazia")
        else:
            logger.warning(f"[BuscarIntegrado] [AVISO] Busca direta retornou sucesso={resposta_direta.get('dat', {}).get('sucesso')}")
            logger.warning(f"[BuscarIntegrado] [AVISO] Resposta completa: {resposta_direta.get('dat', {})}")

        # Se nÃ£o encontrou por busca direta, tentar com perÃ­odo amplo (FALLBACK)
        logger.warning(f"[BuscarIntegrado] Busca direta nÃ£o retornou resultado, tentando com perÃ­odo amplo...")
        
        # PASSO 1 (FALLBACK): Obter dados primÃ¡rios + complementares usando a integraÃ§Ã£o
        hoje = datetime.now()
        periodo_fim = hoje.strftime("%Y-%m-%d")
        periodo_ini = (hoje - timedelta(days=365)).strftime("%Y-%m-%d")

        resposta_integrada = listar_requisicoes_detalhadas(
            id_evento="50",
            periodo_ini=periodo_ini,
            periodo_fim=periodo_fim,
            enriquecer=True
        )

        # Verificar se encontrou a requisiÃ§Ã£o
        if resposta_integrada.get("dat", {}).get("sucesso") != 1:
            logger.warning(f"[BuscarIntegrado] âŒ RequisiÃ§Ã£o {cod_requisicao} NÃƒO ENCONTRADA em nenhuma busca")
            logger.warning(f"[BuscarIntegrado] ðŸ’¡ POSSÃVEIS CAUSAS:")
            logger.warning(f"[BuscarIntegrado]    1. RequisiÃ§Ã£o nÃ£o existe no sistema apLIS")
            logger.warning(f"[BuscarIntegrado]    2. CÃ³digo digitado incorretamente")
            logger.warning(f"[BuscarIntegrado]    3. RequisiÃ§Ã£o foi cancelada ou excluÃ­da")
            logger.warning(f"[BuscarIntegrado]    4. Problema de permissÃ£o/acesso na API apLIS")
            return jsonify({
                "sucesso": 0,
                "erro": "RequisiÃ§Ã£o nÃ£o encontrada no sistema apLIS",
                "detalhes": "Verifique se o cÃ³digo estÃ¡ correto e se a requisiÃ§Ã£o existe no apLIS",
                "codRequisicao": cod_requisicao,
                "sugestoes": [
                    "Confirme o cÃ³digo da requisiÃ§Ã£o",
                    "Verifique se a requisiÃ§Ã£o foi cadastrada no apLIS",
                    "Tente novamente em alguns minutos (pode haver delay de sincronizaÃ§Ã£o)"
                ]
            }), 404

        # PASSO 2: Buscar a requisiÃ§Ã£o especÃ­fica na lista integrada
        lista_requisicoes = resposta_integrada.get("dat", {}).get("lista", [])
        req_encontrada = None

        for req in lista_requisicoes:
            if req.get("dados_primarios", {}).get("codRequisicao") == cod_requisicao:
                req_encontrada = req
                break

        if not req_encontrada:
            logger.warning(f"[BuscarIntegrado] CÃ³digo {cod_requisicao} nÃ£o encontrado na lista integrada")
            return jsonify({
                "sucesso": 0,
                "erro": "RequisiÃ§Ã£o nÃ£o encontrada",
                "codRequisicao": cod_requisicao
            }), 404

        logger.info(f"[BuscarIntegrado] âœ… RequisiÃ§Ã£o encontrada: {cod_requisicao}")

        # PASSO 3: Buscar imagens no S3
        imagens = []
        s3_client = get_s3_client()

        if s3_client:
            try:
                prefixo_lab = cod_requisicao[:4] if len(cod_requisicao) >= 4 else '0040'
                caminho_s3_base = f"lab/Arquivos/Foto/{prefixo_lab}/{cod_requisicao}"

                logger.info(f"[BuscarIntegrado][S3] Buscando imagens em: {caminho_s3_base}")

                response_s3 = s3_client.list_objects_v2(
                    Bucket=S3_BUCKET,
                    Prefix=caminho_s3_base
                )

                if 'Contents' in response_s3:
                    for obj in response_s3['Contents']:
                        key = obj['Key']
                        filename = key.split('/')[-1]

                        if not filename or not filename.startswith(cod_requisicao):
                            continue

                        try:
                            arquivo_local = os.path.join(TEMP_IMAGES_DIR, filename)

                            if not os.path.exists(arquivo_local):
                                logger.info(f"[BuscarIntegrado][S3] Baixando: {key}")
                                s3_client.download_file(S3_BUCKET, key, arquivo_local)
                            else:
                                logger.debug(f"[BuscarIntegrado][S3] JÃ¡ em cache: {filename}")

                            base_url = request.host_url.rstrip('/')
                            url_local = f"{base_url}/api/imagem/{filename}"

                            imagens.append({
                                "nome": filename,
                                "url": url_local,
                                "tamanho": obj['Size'],
                                "dataCadastro": obj['LastModified'].isoformat()
                            })

                        except Exception as e:
                            logger.error(f"[BuscarIntegrado][S3] Erro ao processar {filename}: {e}")

                    logger.info(f"[BuscarIntegrado][S3] âœ… Encontradas {len(imagens)} imagens")
                else:
                    logger.info(f"[BuscarIntegrado][S3] Nenhuma imagem em {caminho_s3_base}")

            except Exception as e:
                logger.error(f"[BuscarIntegrado][S3] Erro ao buscar imagens: {str(e)}")
        else:
            logger.warning("[BuscarIntegrado][S3] Cliente S3 nÃ£o disponÃ­vel")

        # PASSO 4: Montar resposta INTEGRADA com estrutura compatÃ­vel com o frontend
        # Transformar dados integrados para formato esperado pelo frontend
        dados_primarios = req_encontrada.get("dados_primarios", {})
        dados_pac = req_encontrada.get("paciente", {})
        dados_med = req_encontrada.get("medico", {})
        dados_complementares = req_encontrada.get("dados_complementares", {})
        
        # Usar IDs conforme vÃªm da integraÃ§Ã£o - os helpers tratarÃ£o None apropriadamente
        id_convenio_fallback = dados_complementares.get("idConvenio")
        id_local_origem_fallback = dados_complementares.get("idLocalOrigem")
        id_fonte_pagadora_fallback = dados_complementares.get("idFontePagadora")
        id_medico_fallback = dados_complementares.get("idMedico")
        
        logger.info(f"[BuscarIntegrado] ðŸ” FALLBACK - IDs vindos da integraÃ§Ã£o:")
        logger.info(f"[BuscarIntegrado]   - idConvenio: {id_convenio_fallback}")
        logger.info(f"[BuscarIntegrado]   - idLocalOrigem: {id_local_origem_fallback}")
        logger.info(f"[BuscarIntegrado]   - idFontePagadora: {id_fonte_pagadora_fallback}")
        logger.info(f"[BuscarIntegrado]   - idMedico: {id_medico_fallback}")
        logger.info(f"[BuscarIntegrado] ðŸ” FALLBACK - Dados jÃ¡ enriquecidos da req_encontrada:")
        logger.info(f"[BuscarIntegrado]   - convenio: {req_encontrada.get('convenio')}")
        logger.info(f"[BuscarIntegrado]   - localOrigem: {req_encontrada.get('localOrigem')}")
        logger.info(f"[BuscarIntegrado]   - fontePagadora: {req_encontrada.get('fontePagadora')}")
        
        logger.debug(f"[BuscarIntegrado] IDs da integraÃ§Ã£o: convenio={id_convenio_fallback}, fonte={id_fonte_pagadora_fallback}, local={id_local_origem_fallback}, medico={id_medico_fallback}")

        resultado = {
            "sucesso": 1,
            # ===== DADOS PRIMÃRIOS (da integraÃ§Ã£o) =====
            "requisicao": {
                "codRequisicao": dados_primarios.get("codRequisicao"),
                "idRequisicao": dados_primarios.get("idRequisicao"),
                "dtaColeta": dados_primarios.get("dtaColeta"),
                "numGuia": dados_primarios.get("numGuia"),
                "dadosClinicos": dados_primarios.get("dadosClinicos"),
                # Dados complementares da integraÃ§Ã£o (com defaults)
                "idConvenio": id_convenio_fallback,
                "idLocalOrigem": id_local_origem_fallback,
                "idFontePagadora": id_fonte_pagadora_fallback,
                "idMedico": id_medico_fallback,
                # Status da requisiÃ§Ã£o no apLIS: 0=Em andamento, 1=ConcluÃ­do, 2=Cancelado
                "StatusExame": status_exame
            },
            # ===== DADOS DO PACIENTE (CPF Ã© principal - vem do requisicaoListar) =====
            "paciente": {
                "idPaciente": dados_pac.get("idPaciente"),
                "nome": dados_pac.get("nome"),
                "cpf": dados_pac.get("cpf"),  # âœ… PRINCIPAL - Vem do requisicaoListar
                # Dados que virÃ£o do OCR:
                "dtaNasc": dados_pac.get("dtaNasc"),
                "sexo": dados_pac.get("sexo"),
                "rg": dados_pac.get("rg"),
                "telCelular": dados_pac.get("telCelular"),
                "endereco": dados_pac.get("endereco", {})
            },
            # ===== DADOS DO MÃ‰DICO (complementares) =====
            "medico": {
                "nome": dados_med.get("nome"),
                "crm": dados_med.get("crm"),
                "uf": dados_med.get("uf")
            },
            # ===== INFORMAÃ‡Ã•ES DE ORIGEM (complementares) =====
            "convenio": {
                "id": id_convenio_fallback,  # âœ… ID do convÃªnio
                **req_encontrada.get("convenio", {})
            },
            "fontePagadora": {
                "id": id_fonte_pagadora_fallback,  # âœ… ID da fonte pagadora
                **req_encontrada.get("fontePagadora", {})
            },
            "localOrigem": {
                "id": id_local_origem_fallback,  # âœ… ID do local de origem
                **req_encontrada.get("localOrigem", {})
            },
            # ===== IMAGENS =====
            "imagens": imagens,
            "totalImagens": len(imagens),
            # ===== METADATA =====
            "origem": "requisicaoListar_integrado",
            "statusIntegracao": "completo",
            "avisos": [
                "Dados primÃ¡rios: codRequisicao, CPF, nome paciente - do apLIS",
                "Dados complementares: mÃ©dico, convÃªnio, local - enriquecidos",
                "Dados do paciente (dtaNasc, sexo, rg, endereÃ§o) - virÃ£o do OCR"
            ]
        }

        logger.info(f"[BuscarIntegrado] âœ… SUCESSO: {cod_requisicao} ({len(imagens)} imagens) - dados integrados retornados")
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"[BuscarIntegrado] âŒ Erro ao buscar requisiÃ§Ã£o {cod_requisicao}: {str(e)}")
        import traceback
        logger.error(f"[BuscarIntegrado] Traceback: {traceback.format_exc()}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar requisiÃ§Ã£o: {str(e)}"
        }), 500


@app.route('/api/debug/csv-dados', methods=['GET'])
def debug_csv_dados():
    """
    ðŸ§ª ENDPOINT DE DEBUG
    Retorna amostras dos dados carregados dos CSVs
    Ãštil para verificar se os CSVs foram carregados corretamente
    e quais IDs estÃ£o disponÃ­veis
    """
    return jsonify({
        "sucesso": 1,
        "dados": {
            "medicos": {
                "total": len(MEDICOS_CACHE),
                "amostra": list(MEDICOS_CACHE.items())[:3]
            },
            "convenios": {
                "total": len(CONVENIOS_CACHE),
                "amostra": list(CONVENIOS_CACHE.items())[:5],
                "todos_ids": list(CONVENIOS_CACHE.keys())
            },
            "instituicoes": {
                "total": len(INSTITUICOES_CACHE),
                "amostra": list(INSTITUICOES_CACHE.items())[:5],
                "todos_ids": list(INSTITUICOES_CACHE.keys())
            }
        }
    }), 200


@app.route('/api/requisicoes/disponiveis', methods=['POST'])
def requisicoes_disponiveis():
    """
    ðŸ§ª ENDPOINT DE DEBUG/TESTE
    Lista os cÃ³digos de requisiÃ§Ã£o disponÃ­veis para testar
    Ãštil quando o usuÃ¡rio nÃ£o sabe qual cÃ³digo buscar
    
    RequisiÃ§Ã£o:
    {
        "idEvento": "50",
        "periodoIni": "2026-01-01",
        "periodoFim": "2026-01-31"
    }
    """
    try:
        dados = request.json
        
        id_evento = dados.get('idEvento', '50')
        periodo_ini = dados.get('periodoIni')
        periodo_fim = dados.get('periodoFim')
        limite = dados.get('limite', 30)  # Retorna apenas os primeiros 30
        
        if not periodo_ini or not periodo_fim:
            # Usar padrÃ£o: Ãºltimos 30 dias
            hoje = datetime.now()
            periodo_fim = hoje.strftime("%Y-%m-%d")
            periodo_ini = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        
        logger.info(f"[Disponiveis] Listando cÃ³digos disponÃ­veis: evento={id_evento}, perÃ­odo={periodo_ini} a {periodo_fim}")
        
        resposta = listar_requisicoes_detalhadas(id_evento, periodo_ini, periodo_fim, enriquecer=False)
        
        if resposta.get("dat", {}).get("sucesso") != 1:
            return jsonify({
                "sucesso": 0,
                "erro": "Erro ao buscar requisiÃ§Ãµes"
            }), 500
        
        lista_requisicoes = resposta.get("dat", {}).get("lista", [])
        
        # Extrair cÃ³digos e pacientes
        codigos_disponiveis = []
        for req in lista_requisicoes[:limite]:
            codigos_disponiveis.append({
                "codigo": req.get("CodRequisicao"),
                "paciente": req.get("NomPaciente"),
                "cpf": req.get("CPF"),
                "data": req.get("DtaColeta") or req.get("DtaPrevista")
            })
        
        logger.info(f"[Disponiveis] Retornando {len(codigos_disponiveis)} cÃ³digos")
        
        return jsonify({
            "sucesso": 1,
            "total": len(lista_requisicoes),
            "codigos": codigos_disponiveis,
            "mensagem": f"Primeiros {len(codigos_disponiveis)} de {len(lista_requisicoes)} requisiÃ§Ãµes disponÃ­veis"
        }), 200
        
    except Exception as e:
        logger.error(f"[Disponiveis] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao listar requisiÃ§Ãµes disponÃ­veis: {str(e)}"
        }), 500


@app.route('/api/admissao/salvar', methods=['POST'])
def salvar_admissao():
    """
    Endpoint para salvar admissÃ£o
    """
    try:
        dados = request.json
        logger.info(f"[SalvarAdmissao] Iniciando salvamento. Dados recebidos: {json.dumps(dados, indent=2, ensure_ascii=False)[:1000]}")

        # ðŸ†• Extrair credenciais do apLIS do usuÃ¡rio
        aplis_usuario = dados.pop('aplis_usuario', None)
        aplis_senha = dados.pop('aplis_senha', None)
        logger.info(f"[SalvarAdmissao] Credenciais apLIS: usuario={aplis_usuario or 'PADRÃƒO'}")

        # 1. SanitizaÃ§Ã£o de IDs (Top Level)
        campos_ids = ['idPaciente', 'idLaboratorio', 'idUnidade', 'idConvenio', 
                      'idLocalOrigem', 'idFontePagadora', 'idMedico', 'idExame']
        
        for campo in campos_ids:
            if campo in dados:
                if dados[campo] == "" or dados[campo] is None:
                    # Remover campos vazios opcionais para nÃ£o enviar lixo
                    if campo not in ['idPaciente', 'idLaboratorio', 'idUnidade']: 
                        del dados[campo]
                else:
                    try:
                        dados[campo] = int(dados[campo])
                        # Se for 0 e opcional, remover (apLIS pode rejeitar ID 0 como chave estrangeira invÃ¡lida)
                        if dados[campo] == 0 and campo not in ['idPaciente', 'idLaboratorio', 'idUnidade']:
                            del dados[campo]
                    except (ValueError, TypeError):
                        logger.warning(f"[SalvarAdmissao] Aviso: Campo {campo} nÃ£o Ã© numÃ©rico: {dados[campo]}")

        # 2. SanitizaÃ§Ã£o de Data (dtaColeta)
        if 'dtaColeta' in dados and dados['dtaColeta']:
            # Remover hora se houver (apLIS espera YYYY-MM-DD)
            if 'T' in dados['dtaColeta']:
                dados['dtaColeta'] = dados['dtaColeta'].split('T')[0]
            elif ' ' in dados['dtaColeta']:
                dados['dtaColeta'] = dados['dtaColeta'].split(' ')[0]

        # 3. SanitizaÃ§Ã£o de examesConvenio
        if 'examesConvenio' in dados and isinstance(dados['examesConvenio'], list):
            novos_exames = []
            for item in dados['examesConvenio']:
                if isinstance(item, dict):
                    # Se tem idExame, garante que Ã© int
                    # Se for objeto, extrair APENAS o ID (apLIS espera lista de IDs simples, nÃ£o objetos)
                    if 'idExame' in item and item['idExame']:
                        try:
                            novos_exames.append(int(item['idExame']))
                        except:
                            logger.warning(f"[SalvarAdmissao] Erro ao converter idExame: {item}")
                elif isinstance(item, (int, str)) and item:
                    # Se for lista de IDs direto
                    try:
                        novos_exames.append(int(item))
                    except:
                        pass
            dados['examesConvenio'] = novos_exames
            logger.info(f"[SalvarAdmissao] examesConvenio sanitizados: {len(novos_exames)} exames")
            
            # Se lista ficou vazia, remover chave para evitar erro de lista vazia (se apLIS nÃ£o gostar)
            if not novos_exames:
                del dados['examesConvenio']
            else:
                # CRÃTICO: apLIS exige idExame na raiz para validaÃ§Ã£o "Selecione o exame"
                # Usamos o primeiro exame da lista como principal
                dados['idExame'] = novos_exames[0]
        
        # Se veio apenas idExame na raiz e nÃ£o tem lista, criar lista
        if 'idExame' in dados and 'examesConvenio' not in dados:
             dados['examesConvenio'] = [int(dados['idExame'])]

        # IMPORTANTE: NÃƒO remover idExame da raiz - o apLIS precisa TANTO do idExame
        # na raiz QUANTO da lista examesConvenio para funcionar corretamente

        # ðŸ†• 4. Converter fontePagadora (nome) para idFontePagadora (ID) se necessÃ¡rio
        logger.info(f"[SalvarAdmissao] ðŸ” DEBUG: Verificando campo fontePagadora...")
        logger.info(f"[SalvarAdmissao] ðŸ” DEBUG: 'fontePagadora' in dados? {'fontePagadora' in dados}")
        if 'fontePagadora' in dados:
            logger.info(f"[SalvarAdmissao] ðŸ” DEBUG: Valor: {dados['fontePagadora']}, Tipo: {type(dados['fontePagadora'])}")
        
        if 'fontePagadora' in dados and isinstance(dados['fontePagadora'], str):
            nome_fonte = dados['fontePagadora']
            logger.info(f"[SalvarAdmissao] ðŸ” Recebido fontePagadora como nome: '{nome_fonte}'")
            logger.info(f"[SalvarAdmissao] ðŸ”„ Buscando ID da instituiÃ§Ã£o no cache...")
            
            instituicao = buscar_instituicao_por_nome(nome_fonte)
            if instituicao:
                dados['idFontePagadora'] = instituicao['id']
                logger.info(f"[SalvarAdmissao] âœ… Fonte pagadora convertida: '{nome_fonte}' â†’ ID {instituicao['id']}")
                # Remover o campo de nome para nÃ£o causar confusÃ£o
                del dados['fontePagadora']
            else:
                logger.warning(f"[SalvarAdmissao] âš ï¸ Fonte pagadora '{nome_fonte}' nÃ£o encontrada no cache")
                # Manter o campo para tentar usar default depois
                del dados['fontePagadora']

        # 5. Defaults e Limpeza (CAMPOS OBRIGATÃ“RIOS DO APLIS)
        if 'idLaboratorio' not in dados or not dados['idLaboratorio']:
            logger.info("[SalvarAdmissao] idLaboratorio nÃ£o informado, usando default: 1")
            dados['idLaboratorio'] = 1

        if 'idUnidade' not in dados or not dados['idUnidade']:
            logger.info("[SalvarAdmissao] idUnidade nÃ£o informada, usando default: 1")
            dados['idUnidade'] = 1

        # ðŸ†• VERIFICAR SE REQUISIÃ‡ÃƒO JÃ EXISTE (para evitar conflito de fonte pagadora)
        requisicao_existente = None
        fonte_do_ocr = dados.get('_fonte_dados') == 'ocr'  # Flag indicando que os dados vieram do OCR
        
        if 'codRequisicao' in dados and dados['codRequisicao']:
            logger.info(f"[SalvarAdmissao] ðŸ” Verificando se requisiÃ§Ã£o {dados['codRequisicao']} jÃ¡ existe...")
            logger.info(f"[SalvarAdmissao] ðŸ“Š Fonte dos dados: {'OCR (PRIORIDADE)' if fonte_do_ocr else 'Banco/API'}")
            
            try:
                ids_banco = buscar_ids_banco(dados['codRequisicao'])
                if ids_banco and ids_banco.get('IdFontePagadora'):
                    requisicao_existente = ids_banco
                    logger.info(f"[SalvarAdmissao] âœ… RequisiÃ§Ã£o existe! Fonte pagadora no BANCO: {ids_banco.get('IdFontePagadora')}")
                    
                    # ðŸ†• LÃ“GICA DE PRIORIZAÃ‡ÃƒO:
                    # - Se dados vieram do OCR: SEMPRE usar dados do OCR (mais atualizados/corretos)
                    # - Se dados vieram do banco/API: usar dados do banco (manter consistÃªncia)
                    if 'idFontePagadora' in dados and dados['idFontePagadora'] != ids_banco.get('IdFontePagadora'):
                        if fonte_do_ocr:
                            logger.warning(f"[SalvarAdmissao] âš ï¸ DivergÃªncia detectada entre OCR e banco!")
                            logger.warning(f"[SalvarAdmissao]   ðŸ’³ Fonte do OCR (NOVA): {dados['idFontePagadora']}")
                            logger.warning(f"[SalvarAdmissao]   ðŸ’¾ Fonte do BANCO (ANTIGA): {ids_banco.get('IdFontePagadora')}")
                            logger.warning(f"[SalvarAdmissao]   âœ… USANDO DADOS DO OCR (prioridade) para atualizar cadastro")
                            # NÃƒO sobrescrever - manter dados do OCR
                        else:
                            logger.warning(f"[SalvarAdmissao] âš ï¸ Conflito detectado!")
                            logger.warning(f"[SalvarAdmissao]   Fonte informada: {dados['idFontePagadora']}")
                            logger.warning(f"[SalvarAdmissao]   Fonte cadastrada: {ids_banco.get('IdFontePagadora')}")
                            logger.warning(f"[SalvarAdmissao]   ðŸ”„ Usando fonte pagadora jÃ¡ cadastrada para evitar erro do apLIS")
                            dados['idFontePagadora'] = ids_banco.get('IdFontePagadora')
                else:
                    logger.info(f"[SalvarAdmissao] â„¹ï¸ RequisiÃ§Ã£o nÃ£o encontrada ou sem fonte pagadora - serÃ¡ nova requisiÃ§Ã£o")
            except Exception as e:
                logger.error(f"[SalvarAdmissao] Erro ao verificar requisiÃ§Ã£o existente: {e}")

        # CRÃTICO: apLIS exige convÃªnio, fonte pagadora e mÃ©dico (nÃ£o podem ser null/0)
        # Se nÃ£o foram informados, buscar IDs vÃ¡lidos do cache (preferencialmente PARTICULAR)
        if 'idConvenio' not in dados or not dados.get('idConvenio'):
            # Se requisiÃ§Ã£o existe E dados NÃƒO vieram do OCR, usar convÃªnio cadastrado
            if requisicao_existente and requisicao_existente.get('IdConvenio') and not fonte_do_ocr:
                dados['idConvenio'] = requisicao_existente['IdConvenio']
                logger.info(f"[SalvarAdmissao] ðŸ’¾ Usando convÃªnio da requisiÃ§Ã£o existente (banco): {dados['idConvenio']}")
            else:
                id_convenio_default = obter_id_convenio_default()
                if id_convenio_default:
                    logger.info(f"[SalvarAdmissao] idConvenio nÃ£o informado, usando default: {id_convenio_default}")
                    dados['idConvenio'] = id_convenio_default
                else:
                    logger.error("[SalvarAdmissao] âŒ Cache de convÃªnios vazio! NÃ£o Ã© possÃ­vel salvar sem convÃªnio.")
                    return jsonify({
                        "sucesso": 0,
                        "erro": "ConvÃªnio nÃ£o informado e cache de convÃªnios vazio. Configure os dados no sistema."
                    }), 400
        else:
            # Se convÃªnio foi informado E veio do OCR, logar a fonte
            if fonte_do_ocr:
                logger.info(f"[SalvarAdmissao] ðŸ“¸ ConvÃªnio do OCR: {dados['idConvenio']}")

        if 'idFontePagadora' not in dados or not dados.get('idFontePagadora'):
            # Se requisiÃ§Ã£o existe E dados NÃƒO vieram do OCR, usar fonte pagadora cadastrada
            if requisicao_existente and requisicao_existente.get('IdFontePagadora') and not fonte_do_ocr:
                dados['idFontePagadora'] = requisicao_existente['IdFontePagadora']
                logger.info(f"[SalvarAdmissao] ðŸ’¾ Usando fonte pagadora da requisiÃ§Ã£o existente (banco): {dados['idFontePagadora']}")
            else:
                id_instituicao_default = obter_id_instituicao_default()
                if id_instituicao_default:
                    logger.info(f"[SalvarAdmissao] idFontePagadora nÃ£o informada, usando default: {id_instituicao_default}")
                    dados['idFontePagadora'] = id_instituicao_default
                else:
                    logger.error("[SalvarAdmissao] âŒ Cache de instituiÃ§Ãµes vazio! NÃ£o Ã© possÃ­vel salvar sem fonte pagadora.")
                    return jsonify({
                        "sucesso": 0,
                        "erro": "Fonte pagadora nÃ£o informada e cache de instituiÃ§Ãµes vazio. Configure os dados no sistema."
                    }), 400
        else:
            # Se fonte pagadora foi informada E veio do OCR, logar a fonte
            if fonte_do_ocr:
                logger.info(f"[SalvarAdmissao] ðŸ“¸ Fonte pagadora do OCR: {dados['idFontePagadora']}")

        if 'idMedico' not in dados or not dados.get('idMedico'):
            id_medico_default = obter_id_medico_default()
            if id_medico_default:
                logger.info(f"[SalvarAdmissao] idMedico nÃ£o informado, usando default: {id_medico_default}")
                dados['idMedico'] = id_medico_default
            else:
                logger.error("[SalvarAdmissao] âŒ Cache de mÃ©dicos vazio! NÃ£o Ã© possÃ­vel salvar sem mÃ©dico.")
                return jsonify({
                    "sucesso": 0,
                    "erro": "MÃ©dico nÃ£o informado e cache de mÃ©dicos vazio. Configure os dados no sistema."
                }), 400

        if 'codRequisicao' in dados and not dados['codRequisicao']:
            del dados['codRequisicao']

        # ðŸ†• VALIDAR numGuia (deve ter exatamente 9 dÃ­gitos vÃ¡lidos)
        # IMPORTANTE: Para alguns convÃªnios/procedimentos, o numGuia Ã© OBRIGATÃ“RIO
        # Se nÃ£o tiver, o apLIS pode rejeitar dependendo do tipo de exame
        tem_num_guia_valido = False
        if 'numGuia' in dados:
            logger.info(f"[SalvarAdmissao] ðŸ” Campo numGuia recebido: '{dados['numGuia']}' (tipo: {type(dados['numGuia'])})")
            num_guia = str(dados['numGuia']).strip()
            # Remover caracteres nÃ£o numÃ©ricos
            num_guia_limpo = ''.join(filter(str.isdigit, num_guia))
            
            logger.info(f"[SalvarAdmissao] ðŸ” numGuia apÃ³s limpeza: '{num_guia_limpo}' (tamanho: {len(num_guia_limpo)})")
            
            # SÃ³ aceita se tiver exatamente 9 dÃ­gitos E nÃ£o for sÃ³ zeros
            if num_guia_limpo and len(num_guia_limpo) == 9 and num_guia_limpo != '000000000':
                # VÃ¡lido - manter
                dados['numGuia'] = num_guia_limpo
                tem_num_guia_valido = True
                logger.info(f"[SalvarAdmissao] âœ… numGuia vÃ¡lido, serÃ¡ enviado: {num_guia_limpo}")
            else:
                # InvÃ¡lido - remover
                del dados['numGuia']
                logger.warning(f"[SalvarAdmissao] âš ï¸ numGuia invÃ¡lido ou vazio ('{num_guia_limpo}'), campo removido")
                logger.warning(f"[SalvarAdmissao] âš ï¸ ATENÃ‡ÃƒO: Se o apLIS rejeitar, pode ser porque o numGuia Ã© obrigatÃ³rio para este convÃªnio/exame")
        else:
            logger.warning(f"[SalvarAdmissao] âš ï¸ Campo numGuia nÃ£o presente nos dados recebidos")
            logger.warning(f"[SalvarAdmissao] âš ï¸ Alguns convÃªnios exigem nÃºmero da guia. Se o apLIS rejeitar, preencha o campo 'NÃºmero da Guia'")

        # ðŸ†• GERAR numGuia PROVISÃ“RIO se nÃ£o tiver (previne erro do apLIS)
        # Alguns procedimentos (ex: patologia molecular) EXIGEM numGuia obrigatoriamente
        # SoluÃ§Ã£o: usar os Ãºltimos 9 dÃ­gitos do cÃ³digo da requisiÃ§Ã£o como nÃºmero da guia
        if not tem_num_guia_valido and 'codRequisicao' in dados and dados['codRequisicao']:
            cod_req_limpo = ''.join(filter(str.isdigit, str(dados['codRequisicao'])))
            if len(cod_req_limpo) >= 9:
                # Pegar Ãºltimos 9 dÃ­gitos
                num_guia_provisorio = cod_req_limpo[-9:]
                dados['numGuia'] = num_guia_provisorio
                logger.info(f"[SalvarAdmissao] ðŸ”„ numGuia gerado automaticamente (Ãºltimos 9 dÃ­gitos): {num_guia_provisorio}")
                logger.info(f"[SalvarAdmissao] ðŸ’¡ Baseado no cÃ³digo da requisiÃ§Ã£o: {dados['codRequisicao']}")
            else:
                # CÃ³digo muito curto, usar com zeros Ã  esquerda
                num_guia_provisorio = cod_req_limpo.zfill(9)[-9:]
                dados['numGuia'] = num_guia_provisorio
                logger.info(f"[SalvarAdmissao] ðŸ”„ numGuia gerado (cÃ³digo curto, com padding): {num_guia_provisorio}")

        # ðŸ†• LIMPAR campos vazios (apLIS rejeita strings vazias)
        # Remover campos que estÃ£o vazios para evitar erros de validaÃ§Ã£o
        campos_para_limpar = ['matConvenio', 'fontePagadora', 'dadosClinicos']
        for campo in campos_para_limpar:
            if campo in dados and (dados[campo] == '' or dados[campo] is None):
                logger.warning(f"[SalvarAdmissao] âš ï¸ Campo '{campo}' estÃ¡ vazio, removendo do payload")
                del dados[campo]

        # Validar idPaciente > 0 (se fornecido)
        if 'idPaciente' in dados and (not isinstance(dados['idPaciente'], int) or dados['idPaciente'] <= 0):
             return jsonify({
                "sucesso": 0,
                "erro": f"ID do Paciente invÃ¡lido: {dados.get('idPaciente')}"
            }), 400

        # ðŸ†• SE NÃƒO TEM idPaciente, tentar buscar/criar pelo CPF
        if 'idPaciente' not in dados or dados.get('idPaciente') is None or dados.get('idPaciente') == '':
            logger.warning("[SalvarAdmissao] âš ï¸ idPaciente nÃ£o fornecido - tentando buscar/criar paciente pelo CPF")

            # Verificar se temos CPF para buscar (aceitar vÃ¡rios formatos)
            cpf_paciente = dados.get('cpf') or dados.get('NumCPF') or dados.get('CPF')
            nome_paciente = dados.get('nome') or dados.get('nomePaciente') or dados.get('NomPaciente')
            data_nascimento = dados.get('dataNascimento') or dados.get('dtaNasc') or dados.get('DtaNasc') or dados.get('DtaNascimento')

            if not cpf_paciente:
                logger.error("[SalvarAdmissao] âŒ Dados do paciente nÃ£o fornecidos!")
                logger.error(f"[SalvarAdmissao] âŒ Campos recebidos: {list(dados.keys())}")
                logger.error(f"[SalvarAdmissao] âŒ Valores: cpf={dados.get('cpf')}, NumCPF={dados.get('NumCPF')}, CPF={dados.get('CPF')}")
                return jsonify({
                    "sucesso": 0,
                    "erro": "idPaciente nÃ£o informado e CPF nÃ£o encontrado nos dados recebidos. O frontend deve enviar 'cpf', 'NumCPF' ou 'CPF' junto com 'nome'/'NomPaciente' para criar novo paciente."
                }), 400

            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf_paciente))
            logger.info(f"[SalvarAdmissao] ðŸ” Buscando paciente por CPF: {cpf_limpo}")

            # 1. BUSCAR PACIENTE NO BANCO LOCAL (MySQL)
            paciente_encontrado_local = False
            try:
                connection = pymysql.connect(**DB_CONFIG)
                with connection.cursor() as cursor:
                    query = "SELECT CodPaciente, NomPaciente FROM newdb.paciente WHERE CPF = %s LIMIT 1"
                    cursor.execute(query, (cpf_limpo,))
                    resultado = cursor.fetchone()

                    if resultado:
                        # Paciente encontrado no banco local!
                        cod_paciente = resultado[0]
                        nome_encontrado = resultado[1]
                        logger.info(f"[SalvarAdmissao] âœ… Paciente encontrado no banco LOCAL! ID: {cod_paciente} - {nome_encontrado}")
                        dados['idPaciente'] = cod_paciente
                        paciente_encontrado_local = True
                connection.close()
            except Exception as e:
                logger.error(f"[SalvarAdmissao] Erro ao buscar no banco local: {str(e)}")
            
            # 2. SE NÃƒO ENCONTROU LOCAL, BUSCAR NA API DO apLIS
            if not paciente_encontrado_local:
                logger.warning(f"[SalvarAdmissao] âš ï¸ Paciente com CPF {cpf_limpo} nÃ£o encontrado no banco local")
                logger.info(f"[SalvarAdmissao] ðŸ” Buscando paciente na API do apLIS pelo CPF...")
                
                try:
                    # Buscar paciente no apLIS usando pacienteListar
                    dat_busca = {
                        "cpf": cpf_limpo
                    }
                    
                    resposta_aplis = fazer_requisicao_aplis("pacienteListar", dat_busca)
                    
                    if resposta_aplis and resposta_aplis.get("dat", {}).get("sucesso") == 1:
                        lista_pacientes = resposta_aplis.get("dat", {}).get("lista", [])
                        
                        if lista_pacientes and len(lista_pacientes) > 0:
                            # Paciente encontrado no apLIS!
                            paciente_aplis = lista_pacientes[0]
                            id_paciente_aplis = paciente_aplis.get("CodPaciente") or paciente_aplis.get("IdPaciente") or paciente_aplis.get("idPaciente")
                            nome_paciente_aplis = paciente_aplis.get("NomPaciente") or paciente_aplis.get("nomPaciente")
                            
                            logger.info(f"[SalvarAdmissao] âœ… Paciente encontrado na API do apLIS!")
                            logger.info(f"[SalvarAdmissao]   ID: {id_paciente_aplis}")
                            logger.info(f"[SalvarAdmissao]   Nome: {nome_paciente_aplis}")
                            logger.info(f"[SalvarAdmissao]   CPF: {cpf_limpo}")

                            dados['idPaciente'] = id_paciente_aplis
                            paciente_encontrado_local = True  # Marcar como encontrado para nÃ£o criar novo

                            # ðŸ†• SALVAR NO BANCO LOCAL para cache (evita buscar no apLIS toda vez)
                            try:
                                logger.info(f"[SalvarAdmissao] ðŸ’¾ Sincronizando paciente do apLIS para banco LOCAL...")
                                connection_sync = pymysql.connect(**DB_CONFIG)
                                with connection_sync.cursor() as cursor_sync:
                                    query_insert_sync = """
                                        INSERT INTO newdb.paciente
                                        (CodPaciente, NomPaciente, CPF, DtaNasc, NumRG, TelCelular)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                        ON DUPLICATE KEY UPDATE
                                            NomPaciente = VALUES(NomPaciente),
                                            CPF = VALUES(CPF),
                                            DtaNasc = VALUES(DtaNasc),
                                            NumRG = VALUES(NumRG),
                                            TelCelular = VALUES(TelCelular)
                                    """

                                    cursor_sync.execute(query_insert_sync, (
                                        id_paciente_aplis,
                                        nome_paciente_aplis,
                                        cpf_limpo,
                                        paciente_aplis.get('DtaNasc') or paciente_aplis.get('dtaNasc'),
                                        paciente_aplis.get('NumRG') or paciente_aplis.get('rg'),
                                        paciente_aplis.get('TelCelular') or paciente_aplis.get('telefone')
                                    ))
                                    connection_sync.commit()
                                    logger.info(f"[SalvarAdmissao] âœ… Paciente sincronizado no banco LOCAL!")
                                connection_sync.close()
                            except Exception as e_sync:
                                logger.error(f"[SalvarAdmissao] âš ï¸ Erro ao sincronizar no banco local (nÃ£o crÃ­tico): {str(e_sync)}")
                                # NÃ£o interromper o fluxo se falhar a sincronizaÃ§Ã£o
                        else:
                            logger.info(f"[SalvarAdmissao] â„¹ï¸ Paciente com CPF {cpf_limpo} nÃ£o encontrado na API do apLIS")
                    else:
                        logger.warning(f"[SalvarAdmissao] âš ï¸ Erro ao buscar paciente no apLIS: {resposta_aplis}")
                        
                except Exception as e:
                    logger.error(f"[SalvarAdmissao] Erro ao buscar paciente no apLIS: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 3. SE NÃƒO ENCONTROU EM NENHUM LUGAR, CRIAR NOVO PACIENTE
            if not paciente_encontrado_local:
                logger.warning(f"[SalvarAdmissao] âš ï¸ Paciente com CPF {cpf_limpo} nÃ£o encontrado em nenhum sistema")

                try:
                    # Verificar se temos dados mÃ­nimos para criar
                    if not nome_paciente:
                        return jsonify({
                            "sucesso": 0,
                            "erro": "Paciente nÃ£o encontrado no sistema e nome nÃ£o foi fornecido. ImpossÃ­vel criar novo cadastro."
                        }), 400

                    # 2. VALIDAR CPF NA RECEITA FEDERAL
                    logger.info(f"[SalvarAdmissao] ðŸ” Validando CPF {cpf_limpo} na Receita Federal...")
                    dados_receita = consultar_cpf_receita_federal(cpf_limpo, data_nascimento)

                    usa_metodo_sem_cpf = False

                    if not dados_receita or not dados_receita.get('valido'):
                        logger.warning(f"[SalvarAdmissao] âš ï¸ CPF {cpf_limpo} nÃ£o validado pela Receita Federal")
                        logger.info(f"[SalvarAdmissao] ðŸ”„ Usando mÃ©todo alternativo: Paciente sem documento (CPF nÃ£o validado)")
                        usa_metodo_sem_cpf = True

                        # Marcar que estÃ¡ usando mÃ©todo alternativo para retornar aviso ao frontend
                        dados['_aviso_metodo_alternativo'] = True
                        dados['_cpf_nao_validado'] = cpf_limpo
                    else:
                        logger.info(f"[SalvarAdmissao] âœ… CPF validado pela Receita Federal!")
                        logger.info(f"[SalvarAdmissao]   Nome na RF: {dados_receita.get('nome')}")

                    # 3. CRIAR PACIENTE NO apLIS
                    if usa_metodo_sem_cpf:
                        logger.info(f"[SalvarAdmissao] ðŸ“ Criando novo paciente com mÃ©todo 'Sem Documento'...")
                        logger.warning(f"[SalvarAdmissao] âš ï¸ ATENÃ‡ÃƒO: CPF {cpf_limpo} NÃƒO FOI VALIDADO na Receita Federal - usando cpfAusente")
                    else:
                        logger.info(f"[SalvarAdmissao] ðŸ“ Criando novo paciente no sistema...")

                    dat_paciente = {
                        "idEvento": "3",  # Evento de inclusÃ£o de paciente
                        "nome": nome_paciente
                    }

                    # Se CPF foi validado, enviar CPF. Se nÃ£o, usar cpfAusente
                    if usa_metodo_sem_cpf:
                        dat_paciente["cpfAusente"] = "1"  # Paciente sem documento
                    else:
                        dat_paciente["cpf"] = cpf_limpo

                    # Adicionar campos opcionais
                    if data_nascimento:
                        if 'T' in data_nascimento:
                            data_nascimento = data_nascimento.split('T')[0]
                        dat_paciente['dtaNascimento'] = data_nascimento
                    elif dados_receita and dados_receita.get('data_nascimento'):
                        dat_paciente['dtaNascimento'] = dados_receita['data_nascimento']

                    if dados.get('rg'):
                        dat_paciente['rg'] = dados['rg']
                    if dados.get('telefone') or dados.get('telCelular') or dados.get('TelCelular'):
                        dat_paciente['telefone'] = dados.get('telefone') or dados.get('telCelular') or dados.get('TelCelular')
                    if dados.get('email') or dados.get('Email'):
                        dat_paciente['email'] = dados.get('email') or dados.get('Email')
                    if dados.get('sexo') or dados.get('Sexo'):
                        dat_paciente['sexo'] = dados.get('sexo') or dados.get('Sexo')

                    # Log dos dados sendo enviados
                    logger.info(f"[SalvarAdmissao] ðŸ“¤ Enviando para apLIS pacienteSalvar:")
                    logger.info(f"[SalvarAdmissao]   Dados: {json.dumps(dat_paciente, indent=2, ensure_ascii=False)}")

                    # Chamar apLIS para criar
                    resposta_paciente = fazer_requisicao_aplis("pacienteSalvar", dat_paciente)
                    
                    # Log completo da resposta para debug
                    logger.info(f"[SalvarAdmissao] ðŸ“‹ Resposta completa do apLIS pacienteSalvar:")
                    logger.info(f"[SalvarAdmissao]   JSON: {json.dumps(resposta_paciente, indent=2, ensure_ascii=False)}")

                    # Verificar se apLIS retornou resposta vÃ¡lida
                    if not resposta_paciente:
                        logger.error(f"[SalvarAdmissao] âŒ apLIS nÃ£o retornou resposta (None ou vazio)")
                        return jsonify({
                            "sucesso": 0,
                            "erro": "Erro ao criar novo paciente: apLIS nÃ£o retornou resposta"
                        }), 500
                    
                    if resposta_paciente.get("dat", {}).get("sucesso") == 1:
                        # Tentar mÃºltiplos campos possÃ­veis para o ID do paciente
                        dat = resposta_paciente.get("dat", {})
                        novo_id = dat.get("codPaciente") or dat.get("idPaciente") or dat.get("CodPaciente") or dat.get("IdPaciente") or dat.get("id")
                        
                        logger.info(f"[SalvarAdmissao] ðŸ“‹ Campos disponÃ­veis na resposta 'dat': {list(dat.keys())}")
                        logger.info(f"[SalvarAdmissao] ðŸ“‹ Valores dos campos: {json.dumps(dat, ensure_ascii=False)}")
                        
                        if not novo_id:
                            logger.error(f"[SalvarAdmissao] âŒ apLIS retornou sucesso mas nÃ£o encontrou ID do paciente em nenhum campo esperado")
                            logger.error(f"[SalvarAdmissao] âŒ Campos tentados: codPaciente, idPaciente, CodPaciente, IdPaciente, id")
                            logger.error(f"[SalvarAdmissao] âŒ Resposta completa dat: {json.dumps(dat, ensure_ascii=False)}")
                            return jsonify({
                                "sucesso": 0,
                                "erro": f"Erro ao criar novo paciente: apLIS retornou sucesso mas nÃ£o retornou ID do paciente. Campos disponÃ­veis: {list(dat.keys())}"
                            }), 500
                        
                        logger.info(f"[SalvarAdmissao] âœ… Paciente criado com sucesso! ID: {novo_id}")
                        dados['idPaciente'] = novo_id

                        # ðŸ†• VERIFICAR SE NÃƒO HOUVE DUPLICAÃ‡ÃƒO (verificaÃ§Ã£o adicional de seguranÃ§a)
                        if not usa_metodo_sem_cpf and cpf_limpo:
                            try:
                                logger.info(f"[SalvarAdmissao] ðŸ” VERIFICANDO se houve duplicaÃ§Ã£o do paciente (CPF: {cpf_limpo})...")

                                # Buscar todos os pacientes com este CPF no apLIS
                                dat_verificacao = {"cpf": cpf_limpo}
                                resposta_verificacao = fazer_requisicao_aplis("pacienteListar", dat_verificacao)

                                if resposta_verificacao and resposta_verificacao.get("dat", {}).get("sucesso") == 1:
                                    lista_encontrada = resposta_verificacao.get("dat", {}).get("lista", [])
                                    quantidade = len(lista_encontrada)

                                    if quantidade == 1:
                                        logger.info(f"[SalvarAdmissao] âœ… VERIFICAÃ‡ÃƒO OK: Apenas 1 paciente com CPF {cpf_limpo}")
                                        logger.info(f"[SalvarAdmissao]   ID confirmado: {lista_encontrada[0].get('CodPaciente')}")
                                        # Adicionar confirmaÃ§Ã£o para exibir na interface
                                        dados['_verificacao_duplicacao'] = {
                                            'realizada': True,
                                            'status': 'ok',
                                            'mensagem': f'âœ… VerificaÃ§Ã£o OK: Apenas 1 paciente encontrado'
                                        }
                                    elif quantidade > 1:
                                        logger.error(f"[SalvarAdmissao] âŒâŒâŒ DUPLICAÃ‡ÃƒO DETECTADA! âŒâŒâŒ")
                                        logger.error(f"[SalvarAdmissao]   CPF: {cpf_limpo}")
                                        logger.error(f"[SalvarAdmissao]   Quantidade de pacientes encontrados: {quantidade}")
                                        logger.error(f"[SalvarAdmissao]   IDs duplicados: {[p.get('CodPaciente') for p in lista_encontrada]}")
                                        logger.error(f"[SalvarAdmissao]   âš ï¸ AÃ‡ÃƒO NECESSÃRIA: Verificar e remover duplicatas no sistema apLIS!")

                                        # Preparar informaÃ§Ãµes para exibir na interface
                                        pacientes_duplicados = []
                                        for idx, pac in enumerate(lista_encontrada, 1):
                                            logger.error(f"[SalvarAdmissao]   Paciente {idx}: ID={pac.get('CodPaciente')}, Nome={pac.get('NomPaciente')}")
                                            pacientes_duplicados.append({
                                                'id': pac.get('CodPaciente'),
                                                'nome': pac.get('NomPaciente'),
                                                'cpf': cpf_limpo
                                            })

                                        dados['_aviso_duplicacao'] = {
                                            'tipo': 'duplicacao_detectada',
                                            'mensagem': f'âŒ DUPLICAÃ‡ÃƒO DETECTADA! Encontrados {quantidade} pacientes com o mesmo CPF',
                                            'cpf': cpf_limpo,
                                            'quantidade': quantidade,
                                            'pacientes': pacientes_duplicados
                                        }
                                    else:
                                        logger.warning(f"[SalvarAdmissao] âš ï¸ ALERTA: Busca nÃ£o retornou nenhum paciente (esperado 1)")
                                else:
                                    logger.warning(f"[SalvarAdmissao] âš ï¸ NÃ£o foi possÃ­vel verificar duplicaÃ§Ã£o: {resposta_verificacao}")

                            except Exception as e_verif:
                                logger.error(f"[SalvarAdmissao] âš ï¸ Erro ao verificar duplicaÃ§Ã£o (nÃ£o crÃ­tico): {str(e_verif)}")
                                import traceback
                                logger.error(traceback.format_exc())
                                # NÃ£o interromper o fluxo

                        # ðŸ†• SALVAR PACIENTE NO BANCO LOCAL para evitar duplicaÃ§Ã£o futura
                        try:
                            logger.info(f"[SalvarAdmissao] ðŸ’¾ Salvando paciente no banco LOCAL para prevenir duplicaÃ§Ã£o...")
                            connection = pymysql.connect(**DB_CONFIG)
                            with connection.cursor() as cursor:
                                query_insert = """
                                    INSERT INTO newdb.paciente
                                    (CodPaciente, NomPaciente, CPF, DtaNasc, NumRG, TelCelular, DscEndereco, Email)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        NomPaciente = VALUES(NomPaciente),
                                        CPF = VALUES(CPF),
                                        DtaNasc = VALUES(DtaNasc),
                                        NumRG = VALUES(NumRG),
                                        TelCelular = VALUES(TelCelular),
                                        DscEndereco = VALUES(DscEndereco),
                                        Email = VALUES(Email)
                                """

                                cursor.execute(query_insert, (
                                    novo_id,
                                    nome_paciente,
                                    cpf_limpo if not usa_metodo_sem_cpf else None,
                                    dados.get('DtaNasc') or data_nascimento or dat_paciente.get('dtaNascimento'),
                                    dados.get('rg') or dados.get('RGNumero'),
                                    dados.get('telefone') or dados.get('telCelular') or dados.get('TelCelular'),
                                    dados.get('DscEndereco'),
                                    dados.get('email') or dados.get('Email')
                                ))
                                connection.commit()
                                logger.info(f"[SalvarAdmissao] âœ… Paciente {novo_id} salvo no banco LOCAL com sucesso!")
                            connection.close()
                        except Exception as e_local:
                            logger.error(f"[SalvarAdmissao] âš ï¸ Erro ao salvar no banco local (nÃ£o crÃ­tico): {str(e_local)}")
                            # NÃ£o interromper o fluxo se falhar ao salvar no local
                    else:
                        erro_msg = resposta_paciente.get("dat", {}).get("msg") or resposta_paciente.get("dat", {}).get("msgErro") or resposta_paciente.get("msg") or "Erro desconhecido"
                        cod_erro = resposta_paciente.get("dat", {}).get("codErro")
                        logger.error(f"[SalvarAdmissao] âŒ Erro ao criar paciente:")
                        logger.error(f"[SalvarAdmissao]   Mensagem: {erro_msg}")
                        logger.error(f"[SalvarAdmissao]   CÃ³digo erro: {cod_erro}")
                        logger.error(f"[SalvarAdmissao]   Resposta completa: {json.dumps(resposta_paciente, ensure_ascii=False)}")
                        return jsonify({
                            "sucesso": 0,
                            "erro": f"Erro ao criar novo paciente: {erro_msg}"
                        }), 400

                except Exception as e:
                    logger.error(f"[SalvarAdmissao] Erro ao buscar/criar paciente: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return jsonify({
                        "sucesso": 0,
                        "erro": f"Erro ao buscar/criar paciente: {str(e)}"
                    }), 500

        # Validar campos MÃNIMOS obrigatÃ³rios (conforme API apLIS admissaoSalvar)
        campos_obrigatorios = [
            'idPaciente',    # ID do paciente no sistema
            'dtaColeta',     # Data da coleta
            'idLaboratorio', # ID do laboratÃ³rio
            'idUnidade'      # ID da unidade
        ]

        # Campos opcionais mas recomendados (API aceita sem eles)
        # idConvenio, idLocalOrigem, idFontePagadora, idMedico,
        # idExame, examesConvenio, dadosClinicos, numGuia

        campos_faltantes = [campo for campo in campos_obrigatorios if campo not in dados or dados[campo] is None]

        if campos_faltantes:
            erro_msg = f"Campos obrigatÃ³rios faltando: {', '.join(campos_faltantes)}"
            logger.warning(f"[SalvarAdmissao] âŒ {erro_msg}")
            return jsonify({
                "sucesso": 0,
                "erro": erro_msg
            }), 400

        logger.info(f"[SalvarAdmissao] Dados finais para apLIS: {json.dumps(dados, indent=2, ensure_ascii=False)[:1000]}")
        logger.info(f"[SalvarAdmissao] ðŸŽ« Campo numGuia no envio: {'PRESENTE (' + str(dados.get('numGuia')) + ')' if 'numGuia' in dados else 'AUSENTE (nÃ£o serÃ¡ enviado)'}")
        logger.info(f"[SalvarAdmissao] ðŸ” Campos completos enviados:")
        logger.info(f"[SalvarAdmissao]   - codRequisicao: {dados.get('codRequisicao')}")
        logger.info(f"[SalvarAdmissao]   - idPaciente: {dados.get('idPaciente')}")
        logger.info(f"[SalvarAdmissao]   - idMedico: {dados.get('idMedico')}")
        logger.info(f"[SalvarAdmissao]   - idLocalOrigem: {dados.get('idLocalOrigem')}")
        logger.info(f"[SalvarAdmissao]   - dtaColeta: {dados.get('dtaColeta')}")
        logger.info(f"[SalvarAdmissao]   - examesConvenio: {dados.get('examesConvenio')}")

        # Chamar apLIS com credenciais do usuÃ¡rio
        resultado = salvar_admissao_aplis(dados, aplis_usuario, aplis_senha)

        if resultado.get("dat", {}).get("sucesso") == 1:
            cod_requisicao = resultado["dat"].get("codRequisicao")
            logger.info(f"[SalvarAdmissao] âœ… Sucesso! CodRequisicao: {cod_requisicao}")

            # ðŸ†• ATUALIZAR STATUS NO SUPABASE PARA "SALVO"
            if SUPABASE_ENABLED and cod_requisicao:
                try:
                    logger.info(f"[SalvarAdmissao] ðŸ’¾ Atualizando status no Supabase: {cod_requisicao}")

                    # Buscar dados existentes no Supabase
                    resultado_busca = supabase_manager.buscar_requisicao(cod_requisicao)

                    if resultado_busca.get('sucesso') == 1:
                        # RequisiÃ§Ã£o jÃ¡ existe, atualizar status
                        dados_existentes = resultado_busca['dados']

                        # Atualizar apenas o status para "salvo"
                        dados_update = {
                            **dados_existentes,
                            'status': 'salvo',
                            'processado_por': 'sistema_admissao'
                        }

                        # Salvar novamente (irÃ¡ fazer UPDATE)
                        resultado_save = supabase_manager.salvar_requisicao(
                            cod_requisicao=cod_requisicao,
                            dados_paciente=dados_existentes.get('dados_paciente', {}),
                            dados_ocr=dados_existentes.get('dados_ocr'),
                            dados_consolidados=dados_existentes.get('dados_consolidados'),
                            exames=dados_existentes.get('exames'),
                            exames_ids=dados_existentes.get('exames_ids'),
                            processado_por='sistema_admissao'
                        )

                        if resultado_save.get('sucesso') == 1:
                            logger.info(f"[SalvarAdmissao] âœ… Status atualizado no Supabase!")
                        else:
                            logger.warning(f"[SalvarAdmissao] âš ï¸ Erro ao atualizar Supabase: {resultado_save.get('erro')}")
                    else:
                        logger.info(f"[SalvarAdmissao] â„¹ï¸ RequisiÃ§Ã£o nÃ£o encontrada no Supabase (nÃ£o foi processada via OCR)")

                except Exception as e:
                    logger.warning(f"[SalvarAdmissao] âš ï¸ Erro ao atualizar Supabase (continuando): {str(e)}")

            # ðŸ†• CRIAR REQUISIÃ‡ÃƒO CORRESPONDENTE (0085 â†” 0200)
            cod_correspondente = None
            if cod_requisicao and (cod_requisicao.startswith('0085') or cod_requisicao.startswith('0200')):
                try:
                    tipo_atual = '0085' if cod_requisicao.startswith('0085') else '0200'
                    tipo_correspondente = '0200' if tipo_atual == '0085' else '0085'
                    cod_correspondente = tipo_correspondente + cod_requisicao[4:]
                    
                    logger.info(f"[SalvarAdmissao] ðŸ”„ Criando requisiÃ§Ã£o correspondente: {cod_correspondente}")
                    
                    # Copiar todos os dados da requisiÃ§Ã£o original
                    dados_correspondente = dados.copy()
                    
                    # Ajustar campos especÃ­ficos se necessÃ¡rio
                    # O codRequisicao serÃ¡ o correspondente
                    dados_correspondente['codRequisicao'] = cod_correspondente

                    # Chamar apLIS para criar a correspondente com credenciais do usuÃ¡rio
                    resultado_correspondente = salvar_admissao_aplis(dados_correspondente, aplis_usuario, aplis_senha)
                    
                    if resultado_correspondente.get("dat", {}).get("sucesso") == 1:
                        logger.info(f"[SalvarAdmissao] âœ… RequisiÃ§Ã£o correspondente criada: {cod_correspondente}")
                    else:
                        erro_msg = resultado_correspondente.get("dat", {}).get("msg") or "Erro desconhecido"
                        logger.warning(f"[SalvarAdmissao] âš ï¸ Erro ao criar requisiÃ§Ã£o correspondente: {erro_msg}")
                        logger.warning(f"[SalvarAdmissao] âš ï¸ Resposta: {json.dumps(resultado_correspondente, ensure_ascii=False)}")
                        
                except Exception as e:
                    logger.error(f"[SalvarAdmissao] âŒ Erro ao criar requisiÃ§Ã£o correspondente: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())

            # ðŸ†• ============================================
            # ðŸ“ LOG PERMANENTE DE ADMISSÃƒO SALVA
            # ============================================
            try:
                # Extrair dados do paciente para o log
                nome_paciente = dados.get('nomePaciente') or dados.get('nome') or dados.get('NomPaciente') or 'NÃ£o informado'
                cpf_log = dados.get('cpf') or dados.get('CPF') or dados.get('NumCPF') or 'NÃ£o informado'
                id_paciente_log = dados.get('idPaciente', 'NÃ£o informado')
                convenio_log = dados.get('idConvenio', 'NÃ£o informado')
                medico_log = dados.get('idMedico', 'NÃ£o informado')
                data_coleta_log = dados.get('dtaColeta', 'NÃ£o informado')
                
                # Buscar nomes dos relacionamentos (convÃªnio e mÃ©dico) para log mais legÃ­vel
                nome_convenio = 'NÃ£o identificado'
                if convenio_log != 'NÃ£o informado':
                    convenio_info = buscar_convenio_por_id(convenio_log)
                    if convenio_info:
                        nome_convenio = convenio_info.get('nome', 'NÃ£o identificado')
                
                nome_medico = 'NÃ£o identificado'
                if medico_log != 'NÃ£o informado':
                    # Buscar no cache de mÃ©dicos (se houver)
                    for chave, medico_info in MEDICOS_CACHE.items():
                        if str(medico_info.get('id')) == str(medico_log):
                            nome_medico = medico_info.get('nome', 'NÃ£o identificado')
                            break
                
                # Timestamp do salvamento
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Log estruturado e completo
                logger.info("=" * 100)
                logger.info("ðŸ“‹ ADMISSÃƒO SALVA COM SUCESSO")
                logger.info("=" * 100)
                logger.info(f"â° Data/Hora: {timestamp}")
                logger.info(f"ðŸ¥ CÃ³digo RequisiÃ§Ã£o: {cod_requisicao}")
                if cod_correspondente:
                    logger.info(f"ðŸ”— RequisiÃ§Ã£o Correspondente: {cod_correspondente}")
                logger.info("-" * 100)
                logger.info("ðŸ‘¤ DADOS DO PACIENTE:")
                logger.info(f"   â€¢ Nome: {nome_paciente}")
                logger.info(f"   â€¢ CPF: {cpf_log}")
                logger.info(f"   â€¢ ID Paciente: {id_paciente_log}")
                logger.info("-" * 100)
                logger.info("ðŸ¢ DADOS DO ATENDIMENTO:")
                logger.info(f"   â€¢ ConvÃªnio: {nome_convenio} (ID: {convenio_log})")
                logger.info(f"   â€¢ MÃ©dico: {nome_medico} (ID: {medico_log})")
                logger.info(f"   â€¢ Data Coleta: {data_coleta_log}")
                
                # Exames (se houver)
                if 'examesConvenio' in dados and dados['examesConvenio']:
                    exames_ids = dados['examesConvenio']
                    logger.info(f"   â€¢ Exames: {len(exames_ids)} exame(s) - IDs: {exames_ids}")
                
                # Avisos especiais
                if dados.get('_aviso_metodo_alternativo'):
                    logger.info("-" * 100)
                    logger.info("âš ï¸ AVISOS:")
                    logger.info(f"   â€¢ CPF nÃ£o validado na Receita Federal: {dados.get('_cpf_nao_validado')}")
                
                if dados.get('_aviso_duplicacao'):
                    logger.info("   âš ï¸ DUPLICAÃ‡ÃƒO DETECTADA - Ver detalhes acima")
                
                logger.info("=" * 100)
                
            except Exception as e_log:
                logger.error(f"[SalvarAdmissao] âš ï¸ Erro ao gerar log de admissÃ£o salva: {e_log}")
            # ============================================

            # Preparar resposta com aviso se usou mÃ©todo alternativo
            resposta = {
                "sucesso": 1,
                "mensagem": "AdmissÃ£o salva com sucesso!",
                "codRequisicao": cod_requisicao,
                "dados": resultado["dat"]
            }

            # ðŸ†• ADICIONAR AVISOS DE DUPLICAÃ‡ÃƒO E VERIFICAÃ‡ÃƒO
            if dados.get('_aviso_duplicacao'):
                resposta['aviso_duplicacao'] = dados['_aviso_duplicacao']

            if dados.get('_verificacao_duplicacao'):
                resposta['verificacao_duplicacao'] = dados['_verificacao_duplicacao']

            if dados.get('_aviso_metodo_alternativo'):
                resposta['aviso_metodo_alternativo'] = {
                    'tipo': 'cpf_nao_validado',
                    'mensagem': f"âš ï¸ Paciente cadastrado com mÃ©todo alternativo (CPF nÃ£o validado na Receita Federal)",
                    'cpf': dados.get('_cpf_nao_validado')
                }

            # Adicionar cÃ³digo da correspondente se foi criada
            if cod_correspondente:
                resposta["codRequisicaoCorrespondente"] = cod_correspondente
                resposta["mensagem"] = f"AdmissÃ£o salva com sucesso! (Principal: {cod_requisicao}, Correspondente: {cod_correspondente})"
            
            # Adicionar aviso se CPF nÃ£o foi validado
            if dados.get('_aviso_metodo_alternativo'):
                cpf_nao_validado = dados.get('_cpf_nao_validado', 'nÃ£o informado')
                resposta["aviso"] = {
                    "tipo": "cpf_nao_validado",
                    "mensagem": f"âš ï¸ ATENÃ‡ÃƒO: Paciente cadastrado com mÃ©todo alternativo (CPF {cpf_nao_validado} nÃ£o foi validado na Receita Federal). Verifique os dados do paciente.",
                    "cpf": cpf_nao_validado
                }
                logger.warning(f"[SalvarAdmissao] âš ï¸ Retornando aviso de CPF nÃ£o validado: {cpf_nao_validado}")

            return jsonify(resposta), 200
        else:
            # Tentar extrair erro de vÃ¡rios lugares (topo ou dentro de dat)
            erro_aplis = resultado.get("erro")
            msg_aplis = resultado.get("msg")
            cod_erro = resultado.get("dat", {}).get("codErro") if isinstance(resultado.get("dat"), dict) else None
            msg_erro = resultado.get("dat", {}).get("msgErro") if isinstance(resultado.get("dat"), dict) else None
            
            # Se nÃ£o tem erro no topo, procurar dentro de 'dat'
            if not erro_aplis and not msg_aplis:
                dat = resultado.get("dat", {})
                if isinstance(dat, dict):
                    erro_aplis = dat.get("erro") or dat.get("mensagem") or dat.get("msg") or msg_erro
            
            if not erro_aplis:
                # Se nÃ£o encontrou erro legÃ­vel, retornar o dump do objeto para debug
                erro_aplis = f"Erro nÃ£o identificado no retorno do apLIS: {json.dumps(resultado, ensure_ascii=False)}"
            
            # Se for erro de numGuia, adicionar informaÃ§Ã£o de debug
            if "Guia ConvÃªnio" in str(erro_aplis) or "numGuia" in str(erro_aplis):
                num_guia_enviado = dados.get('numGuia', 'NÃƒO ENVIADO')
                erro_aplis = (
                    f"âŒ {erro_aplis}\n\n"
                    f"ðŸ” DEBUG: numGuia enviado = '{num_guia_enviado}' (tamanho: {len(str(num_guia_enviado)) if num_guia_enviado != 'NÃƒO ENVIADO' else 0})\n\n"
                    f"ðŸ’¡ CAUSA: O convÃªnio/procedimento selecionado EXIGE o nÃºmero da guia (9 dÃ­gitos).\n\n"
                    f"ðŸ”§ SOLUÃ‡ÃƒO:\n"
                    f"  1. Localize o campo 'NÃºmero da Guia' no formulÃ¡rio (lado direito)\n"
                    f"  2. Preencha com 9 dÃ­gitos numÃ©ricos (ex: 123456789)\n"
                    f"  3. Tente salvar novamente\n\n"
                    f"ðŸ“ ALTERNATIVA: Se nÃ£o tiver o nÃºmero da guia:\n"
                    f"  - Entre em contato com o convÃªnio para obter\n"
                    f"  - Ou use '000000001' como nÃºmero provisÃ³rio"
                )
            
            # Se for erro de fonte pagadora conflitante, adicionar explicaÃ§Ã£o
            if "fonte pagadora" in str(erro_aplis).lower() or "procedimentos cobrados" in str(erro_aplis).lower():
                logger.error(f"[SalvarAdmissao] ðŸ” ERRO DE FONTE PAGADORA DETECTADO")
                logger.error(f"[SalvarAdmissao]   Fonte pagadora enviada: {dados.get('idFontePagadora')}")
                logger.error(f"[SalvarAdmissao]   ConvÃªnio enviado: {dados.get('idConvenio')}")
                logger.error(f"[SalvarAdmissao]   CÃ³digo requisiÃ§Ã£o: {dados.get('codRequisicao')}")
                
                # Adicionar dica de soluÃ§Ã£o
                erro_aplis = (
                    f"{erro_aplis}\n\n"
                    f"ðŸ’¡ CAUSA: A requisiÃ§Ã£o jÃ¡ existe no sistema com outra fonte pagadora. "
                    f"O apLIS nÃ£o permite alterar a fonte pagadora de uma requisiÃ§Ã£o existente.\n\n"
                    f"ðŸ”§ SOLUÃ‡ÃƒO: O sistema tentarÃ¡ usar automaticamente a fonte pagadora jÃ¡ cadastrada. "
                    f"Recarregue a pÃ¡gina e tente novamente."
                )
            
            msg_final = f"{erro_aplis} {msg_aplis or ''}".strip()
            logger.error(f"[SalvarAdmissao] âŒ ERRO DO apLIS: {msg_final}")
            logger.error(f"[SalvarAdmissao] âŒ CodErro: {cod_erro}, MsgErro: {msg_erro}")
            logger.error(f"[SalvarAdmissao] âŒ Resposta completa: {json.dumps(resultado, ensure_ascii=False)}")
            return jsonify({
                "sucesso": 0,
                "erro": msg_final,
                "detalhes": resultado
            }), 400

    except Exception as e:
        logger.error(f"[SalvarAdmissao] ðŸ’¥ Erro exceÃ§Ã£o: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro no servidor: {str(e)}"
        }), 500


@app.route('/api/convenios/buscar-por-nome', methods=['POST'])
def buscar_convenio_por_nome():
    """
    Busca convÃªnio por nome (para preencher ID quando OCR encontra carteirinha)
    """
    try:
        dados = request.json
        nome_convenio = dados.get('nome_convenio', '').strip().upper()

        if not nome_convenio:
            return jsonify({
                "sucesso": 0,
                "erro": "Nome do convÃªnio nÃ£o fornecido"
            }), 400

        logger.info(f"[CONVENIO] Procurando convÃªnio: {nome_convenio}")

        # Buscar no cache de convÃªnios carregado
        for id_convenio, convenio_data in CONVENIOS_CACHE.items():
            if convenio_data.get('nome', '').strip().upper() == nome_convenio:
                logger.info(f"[CONVENIO] âœ… Encontrado: ID={id_convenio}, Nome={convenio_data.get('nome')}")
                return jsonify({
                    "sucesso": 1,
                    "idConvenio": int(id_convenio),
                    "nomeConvenio": convenio_data.get('nome')
                }), 200

        # Se nÃ£o encontrarÃ¡ exato, tentar busca parcial (contÃ©m)
        for id_convenio, convenio_data in CONVENIOS_CACHE.items():
            if nome_convenio in convenio_data.get('nome', '').strip().upper():
                logger.info(f"[CONVENIO] âœ… Encontrado (busca parcial): ID={id_convenio}, Nome={convenio_data.get('nome')}")
                return jsonify({
                    "sucesso": 1,
                    "idConvenio": int(id_convenio),
                    "nomeConvenio": convenio_data.get('nome')
                }), 200

        logger.warning(f"[CONVENIO] âŒ ConvÃªnio nÃ£o encontrado: {nome_convenio}")
        return jsonify({
            "sucesso": 0,
            "erro": f"ConvÃªnio '{nome_convenio}' nÃ£o encontrado"
        }), 404

    except Exception as e:
        logger.error(f"[CONVENIO] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar convÃªnio: {str(e)}"
        }), 500


@app.route('/api/admissao/validar', methods=['POST'])
def validar_dados():
    """
    Valida dados antes de salvar
    """
    try:
        dados = request.json
        erros = []
        avisos = []

        # Validar formato de data
        if 'dtaColeta' in dados:
            try:
                datetime.strptime(dados['dtaColeta'], '%Y-%m-%d')
            except ValueError:
                erros.append("Data de coleta invÃ¡lida. Use formato YYYY-MM-DD")

        # Validar IDs positivos
        campos_id = ['idLaboratorio', 'idUnidade', 'idPaciente', 'idConvenio',
                     'idLocalOrigem', 'idFontePagadora', 'idMedico', 'idExame']

        for campo in campos_id:
            if campo in dados and (not isinstance(dados[campo], int) or dados[campo] <= 0):
                erros.append(f"{campo} deve ser um nÃºmero inteiro positivo")

        # Validar array de exames
        if 'examesConvenio' in dados:
            if not isinstance(dados['examesConvenio'], list) or len(dados['examesConvenio']) == 0:
                erros.append("examesConvenio deve ser um array com pelo menos um exame")

        # Avisos
        if 'numGuia' not in dados:
            avisos.append("NÃºmero da guia nÃ£o informado")

        if 'dadosClinicos' not in dados:
            avisos.append("Dados clÃ­nicos nÃ£o informados")

        return jsonify({
            "valido": len(erros) == 0,
            "erros": erros,
            "avisos": avisos
        }), 200

    except Exception as e:
        return jsonify({
            "valido": False,
            "erros": [f"Erro ao validar: {str(e)}"]
        }), 500


@app.route('/api/admissao/validar-cpf', methods=['POST'])
def validar_cpf_endpoint():
    """
    Valida CPF na Receita Federal

    Recebe:
        {
            "cpf": "123.456.789-00",
            "data_nascimento": "01/01/1990" (opcional),
            "nome_ocr": "FULANO DE TAL" (opcional - do OCR),
            "data_nascimento_ocr": "01/01/1990" (opcional - do OCR)
        }

    Retorna:
        {
            "sucesso": 1,
            "dados_receita_federal": {
                "nome": "FULANO DE TAL",
                "cpf": "123.456.789-00",
                "data_nascimento": "01/01/1990",
                "situacao_cadastral": "Regular"
            },
            "comparacao": {
                "nome": {
                    "sistema": "FULANO",
                    "receita_federal": "FULANO DE TAL",
                    "divergente": true
                },
                ...
            }
        }
    """
    try:
        dados = request.json
        cpf = dados.get('cpf')
        data_nascimento = dados.get('data_nascimento')
        nome_ocr = dados.get('nome_ocr', '')
        data_nascimento_ocr = dados.get('data_nascimento_ocr', '')

        if not cpf:
            return jsonify({
                "sucesso": 0,
                "mensagem": "CPF nÃ£o informado"
            }), 400

        logger.info(f"[ValidarCPF] Recebida solicitaÃ§Ã£o de validaÃ§Ã£o: CPF={cpf}")
        logger.info(f"[ValidarCPF] Dados do OCR: Nome='{nome_ocr}', Data Nasc='{data_nascimento_ocr}'")

        # Consultar Receita Federal
        dados_receita = consultar_cpf_receita_federal(cpf, data_nascimento or data_nascimento_ocr)

        if dados_receita:
            logger.info(f"[ValidarCPF] âœ… CPF validado com sucesso: {dados_receita.get('nome')}")
            
            # Preparar comparaÃ§Ã£o de dados
            comparacao = {
                "nome": {
                    "sistema": nome_ocr,
                    "receita_federal": dados_receita.get('nome', ''),
                    "divergente": bool(nome_ocr and dados_receita.get('nome') and 
                                      nome_ocr.upper().strip() != dados_receita.get('nome', '').upper().strip())
                },
                "cpf": {
                    "sistema": cpf,
                    "receita_federal": dados_receita.get('cpf', ''),
                    "divergente": False  # CPF sempre serÃ¡ igual (usado para buscar)
                },
                "data_nascimento": {
                    "sistema": data_nascimento_ocr,
                    "receita_federal": dados_receita.get('data_nascimento', ''),
                    "divergente": bool(data_nascimento_ocr and dados_receita.get('data_nascimento') and
                                      data_nascimento_ocr.replace('/', '').replace('-', '') != 
                                      dados_receita.get('data_nascimento', '').replace('/', '').replace('-', ''))
                }
            }
            
            logger.info(f"[ValidarCPF] ðŸ“Š ComparaÃ§Ã£o preparada:")
            logger.info(f"[ValidarCPF]   Nome: '{comparacao['nome']['sistema']}' vs '{comparacao['nome']['receita_federal']}' (divergente: {comparacao['nome']['divergente']})")
            logger.info(f"[ValidarCPF]   Data: '{comparacao['data_nascimento']['sistema']}' vs '{comparacao['data_nascimento']['receita_federal']}' (divergente: {comparacao['data_nascimento']['divergente']})")
            
            return jsonify({
                "sucesso": 1,
                "mensagem": "CPF validado com sucesso",
                "dados_receita_federal": dados_receita,
                "comparacao": comparacao
            }), 200
        else:
            logger.warning(f"[ValidarCPF] âŒ NÃ£o foi possÃ­vel validar o CPF")
            return jsonify({
                "sucesso": 0,
                "mensagem": "NÃ£o foi possÃ­vel validar o CPF na Receita Federal"
            }), 400

    except Exception as e:
        logger.error(f"[ValidarCPF] ðŸ’¥ Erro ao validar CPF: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "mensagem": f"Erro ao validar CPF: {str(e)}"
        }), 500


@app.route('/', methods=['GET'])
def index():
    """
    PÃ¡gina inicial - informaÃ§Ãµes da API
    """
    return jsonify({
        "nome": "API de AdmissÃ£o - Sistema Lab",
        "versao": "2.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/api/health",
            "teste_aplis": "/api/admissao/teste",
            "listar_requisicoes": "/api/requisicoes/listar (POST) - Nova metodologia requisicaoListar",
            "buscar_requisicao": "/api/requisicao/<codigo>",
            "salvar_admissao": "/api/admissao/salvar (POST)",
            "validar_dados": "/api/admissao/validar (POST)",
            "validar_cpf": "/api/admissao/validar-cpf (POST)",
            "processar_ocr": "/api/ocr/processar (POST)",
            "consolidar_resultados": "/api/consolidar-resultados (POST)",
            "buscar_exames": "/api/exames/buscar-por-nome (POST)",
            "servir_imagem": "/api/imagem/<filename>"
        },
        "documentacao": "Veja README.md para mais informaÃ§Ãµes",
        "nota": "API agora usa metodologia requisicaoListar do apiaplisreduzido"
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check do servidor
    """
    return jsonify({
        "status": "online",
        "servico": "API AdmissÃ£o apLIS",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/api/admissao/teste', methods=['GET'])
def teste_conexao():
    """
    Testa conexÃ£o com apLIS
    """
    try:
        response = requests.get(APLIS_URL, timeout=10)
        return jsonify({
            "conexao_ok": True,
            "status_code": response.status_code,
            "mensagem": "ConexÃ£o com apLIS estabelecida"
        }), 200
    except Exception as e:
        return jsonify({
            "conexao_ok": False,
            "erro": str(e),
            "mensagem": "Falha ao conectar com apLIS"
        }), 500


@app.route('/api/imagem/<filename>', methods=['GET'])
def servir_imagem(filename):
    """
    Serve imagem do diretÃ³rio temporÃ¡rio
    """
    try:
        arquivo_path = os.path.join(TEMP_IMAGES_DIR, filename)
        if os.path.exists(arquivo_path):
            # Detectar mimetype baseado na extensÃ£o
            ext = filename.split('.')[-1].upper() if '.' in filename else ''
            mimetype = 'image/png'

            if ext == 'PDF':
                mimetype = 'application/pdf'
            elif ext in ['JPG', 'JPEG']:
                mimetype = 'image/jpeg'
            elif ext == 'PNG':
                mimetype = 'image/png'

            return send_file(arquivo_path, mimetype=mimetype)
        else:
            return jsonify({"erro": "Imagem nÃ£o encontrada"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/ocr/teste', methods=['GET'])
def teste_ocr():
    """Endpoint de teste para verificar se Vertex AI está funcionando"""
    try:
        model = GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Responda apenas: OK")
        return jsonify({"sucesso": 1, "resposta": response.text.strip(), "modelo": "gemini-2.5-flash"})
    except Exception as e:
        import traceback
        return jsonify({"sucesso": 0, "erro": str(e), "traceback": traceback.format_exc()}), 500


@app.route('/api/ocr/processar', methods=['POST'])
def processar_ocr():
    """
    Processa OCR em uma imagem usando Vertex AI e extrai dados
    Aceita tanto URL (de S3) quanto nome de arquivo local
    """
    try:
        dados = request.json
        imagem_nome = dados.get('imagemNome')
        imagem_url = dados.get('imagemUrl')

        if not imagem_nome:
            return jsonify({"sucesso": 0, "erro": "Nome da imagem nÃ£o fornecido"}), 400

        logger.info(f"[OCR] Iniciando processamento: {imagem_nome}")
        logger.debug(f"[OCR] URL recebida: {imagem_url}")

        # Tentar primeiro em arquivo local, depois em S3 via URL
        arquivo_path = os.path.join(TEMP_IMAGES_DIR, imagem_nome)
        image_bytes = None

        # 1. Tentar arquivo local
        if os.path.exists(arquivo_path):
            logger.info(f"[OCR] Carregando de arquivo local: {arquivo_path}")
            with open(arquivo_path, 'rb') as f:
                image_bytes = f.read()
        # 2. Se nÃ£o existe local, tentar S3 via URL
        elif imagem_url:
            logger.info(f"[OCR] Carregando de S3 via URL: {imagem_url}")
            try:
                response = requests.get(imagem_url, timeout=30)
                if response.status_code == 200:
                    image_bytes = response.content
                    logger.info(f"[OCR] Imagem baixada do S3 com sucesso: {len(image_bytes)} bytes")
                else:
                    logger.error(f"[OCR] Erro ao baixar imagem: status {response.status_code}")
                    return jsonify({
                        "sucesso": 0,
                        "erro": f"Erro ao baixar imagem do S3: status {response.status_code}"
                    }), 400
            except Exception as e:
                logger.error(f"[OCR] Erro ao baixar de S3: {str(e)}")
                return jsonify({
                    "sucesso": 0,
                    "erro": f"Erro ao baixar imagem: {str(e)}"
                }), 400
        else:
            logger.error(f"[OCR] Imagem nÃ£o encontrada: {imagem_nome}")
            return jsonify({
                "sucesso": 0,
                "erro": "Imagem nÃ£o encontrada (nem arquivo local nem URL fornecida)"
            }), 404

        if not image_bytes:
            logger.error(f"[OCR] Falha ao carregar dados da imagem: {imagem_nome}")
            return jsonify({
                "sucesso": 0,
                "erro": "Falha ao carregar dados da imagem"
            }), 400

        # Criar modelo Gemini (usando 2.5 Flash - estável e com boa cota)
        model = GenerativeModel("gemini-2.5-flash")

        # Detectar mime type baseado na extensÃ£o
        ext = imagem_nome.split('.')[-1].upper()
        if ext == 'PNG':
            mime_type = "image/png"
        elif ext == 'PDF':
            mime_type = "application/pdf"
        elif ext in ['JPG', 'JPEG']:
            mime_type = "image/jpeg"
        else:
            mime_type = "image/jpeg"

        logger.info(f"[OCR] Tipo MIME detectado: {mime_type}")

        # Criar parte da imagem/documento
        image_part = Part.from_data(data=image_bytes, mime_type=mime_type)

        # âš¡ APLICAR RATE LIMITING ANTES DE CHAMAR VERTEX AI
        logger.info("[OCR] â³ Verificando rate limit...")
        vertex_rate_limiter.wait_if_needed()
        logger.info("[OCR] âœ… Rate limit OK, prosseguindo com requisiÃ§Ã£o")

        # Prompt para extrair dados com rastreabilidade (importado de prompts_ocr.py)
        prompt = gerar_prompt_ocr(imagem_nome)

        # Gerar resposta com retry em caso de rate limit
        logger.info("[OCR] Enviando para Vertex AI...")
        max_retries = 3
        retry_delay = 15  # ComeÃ§ar com 15 segundos

        for attempt in range(max_retries):
            try:
                response = model.generate_content([prompt, image_part])
                texto_resposta = response.text.strip()
                logger.info(f"[OCR] âœ… Resposta recebida do Vertex AI: {len(texto_resposta)} caracteres")
                logger.debug(f"[OCR] Primeiros 500 chars: {texto_resposta[:500]}...")
                break  # Sucesso, sair do loop
            except Exception as e:
                error_str = str(e)
                logger.error(f"[OCR] Erro na tentativa {attempt + 1}/{max_retries}: {error_str}")

                # Se for erro 429 (rate limit) e ainda tem tentativas, aguardar
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 15s, 30s, 60s
                    logger.warning(f"[OCR] â³ Rate limit 429 detectado. Aguardando {wait_time}s antes de tentar novamente...")
                    time.sleep(wait_time)
                    continue

                # Se nÃ£o Ã© 429 ou Ã© a Ãºltima tentativa, retornar erro
                return jsonify({
                    "sucesso": 0,
                    "erro": f"Erro ao processar com Vertex AI: {error_str}"
                }), 500

        # Salvar resposta completa em arquivo de debug
        try:
            debug_path = os.path.join(TEMP_IMAGES_DIR, f"debug_ocr_{imagem_nome}.json")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(texto_resposta)
            logger.debug(f"[OCR] Debug salvo em: {debug_path}")
        except Exception as e:
            logger.warning(f"[OCR] Aviso ao salvar debug: {e}")

        # Limpar possÃ­veis markdown do JSON
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta.replace("```json", "").replace("```", "").strip()
        elif texto_resposta.startswith("```"):
            texto_resposta = texto_resposta.replace("```", "").strip()

        # Parse do JSON
        try:
            dados_extraidos = json.loads(texto_resposta)
            logger.info(f"[OCR] JSON parseado com sucesso")
            logger.debug(f"[OCR] Tipo de documento: {dados_extraidos.get('tipo_documento')}")
            print(f"[OCR]  DEBUG - itens_exame RAW: {dados_extraidos.get('requisicao', {}).get('itens_exame')}")

            # ðŸ†• VALIDAÃ‡ÃƒO E CORREÃ‡ÃƒO AUTOMÃTICA DE DATAS
            def validar_e_corrigir_data(data_str, campo_nome="data"):
                """
                Valida e corrige datas no formato YYYY-MM-DD
                Detecta se dia/mÃªs foram invertidos e corrige automaticamente
                """
                if not data_str or not isinstance(data_str, str):
                    return data_str

                try:
                    # Formato esperado: YYYY-MM-DD
                    partes = data_str.split('-')
                    if len(partes) != 3:
                        return data_str

                    ano, mes, dia = partes
                    ano_int = int(ano)
                    mes_int = int(mes)
                    dia_int = int(dia)

                    # ValidaÃ§Ã£o bÃ¡sica
                    if mes_int < 1 or mes_int > 12:
                        # MÃªs invÃ¡lido! Provavelmente inverteu com dia
                        if dia_int >= 1 and dia_int <= 12:
                            # Dia estÃ¡ na faixa de mÃªs vÃ¡lido, provavelmente inverteu
                            print(f"[OCR] âš ï¸ CORREÃ‡ÃƒO AUTOMÃTICA: {campo_nome}")
                            print(f"[OCR]   Data INCORRETA: {data_str} (mÃªs={mes_int} invÃ¡lido)")
                            print(f"[OCR]   Invertendo dia â†” mÃªs...")
                            data_corrigida = f"{ano}-{dia:02d}-{mes:02d}"
                            print(f"[OCR]   Data CORRIGIDA: {data_corrigida}")
                            return data_corrigida

                    # Se dia Ã© invÃ¡lido para o mÃªs, tambÃ©m pode ser inversÃ£o
                    if dia_int > 31 or dia_int < 1:
                        print(f"[OCR] âš ï¸ Data com dia invÃ¡lido: {data_str} (dia={dia_int})")

                    return data_str

                except (ValueError, IndexError) as e:
                    print(f"[OCR] âš ï¸ Erro ao validar data {data_str}: {e}")
                    return data_str

            # Aplicar validaÃ§Ã£o nas datas do paciente
            if 'paciente' in dados_extraidos:
                paciente = dados_extraidos['paciente']

                # Validar Data de Nascimento
                if 'DtaNascimento' in paciente and isinstance(paciente['DtaNascimento'], dict):
                    data_original = paciente['DtaNascimento'].get('valor')
                    data_corrigida = validar_e_corrigir_data(data_original, "Data de Nascimento")
                    if data_corrigida != data_original:
                        paciente['DtaNascimento'] = {
                            "valor": data_corrigida,
                            "fonte": f"Calculado de idade: {data_original}",
                            "confianca": 0.85  # ConfianÃ§a um pouco menor pois Ã© calculado
                        }
                        print(f"[OCR] âœ… Data de nascimento corrigida: {data_corrigida}")

                # Validar Data de Coleta
                if 'requisicao' in dados_extraidos and 'dtaColeta' in dados_extraidos['requisicao']:
                    if isinstance(dados_extraidos['requisicao']['dtaColeta'], dict):
                        data_original = dados_extraidos['requisicao']['dtaColeta'].get('valor')
                        data_corrigida = validar_e_corrigir_data(data_original, "Data de Coleta")
                        if data_corrigida != data_original:
                            dados_extraidos['requisicao']['dtaColeta']['valor'] = data_corrigida
                            if 'confianca' in dados_extraidos['requisicao']['dtaColeta']:
                                dados_extraidos['requisicao']['dtaColeta']['confianca'] = max(0.7, dados_extraidos['requisicao']['dtaColeta'].get('confianca', 0.9) - 0.2)

            # LOG DETALHADO DOS DADOS DO PACIENTE
            if 'paciente' in dados_extraidos:
                print(f"[OCR]  DADOS DO PACIENTE EXTRAÃDOS ")
                paciente = dados_extraidos['paciente']

                # Nome
                nome = paciente.get('NomPaciente', {}).get('valor') if isinstance(paciente.get('NomPaciente'), dict) else paciente.get('NomPaciente')
                print(f"[OCR]    Nome: {nome}")

                # Data de Nascimento
                data_nasc = paciente.get('DtaNascimento', {}).get('valor') if isinstance(paciente.get('DtaNascimento'), dict) else paciente.get('DtaNascimento')
                print(f"[OCR]    Data Nascimento: {data_nasc}")

                # CPF
                cpf = paciente.get('NumCPF', {}).get('valor') if isinstance(paciente.get('NumCPF'), dict) else paciente.get('NumCPF')
                print(f"[OCR]    CPF: {cpf}")

                # RG
                rg = paciente.get('NumRG', {}).get('valor') if isinstance(paciente.get('NumRG'), dict) else paciente.get('NumRG')
                print(f"[OCR]    RG: {rg}")

                # Telefone
                tel = paciente.get('TelCelular', {}).get('valor') if isinstance(paciente.get('TelCelular'), dict) else paciente.get('TelCelular')
                print(f"[OCR]    Telefone: {tel}")

                # EndereÃ§o
                end = paciente.get('DscEndereco', {}).get('valor') if isinstance(paciente.get('DscEndereco'), dict) else paciente.get('DscEndereco')
                print(f"[OCR]    EndereÃ§o: {end}")

                print(f"[OCR] ")
            else:
                print(f"[OCR]  ATENÃ‡ÃƒO: Nenhum dado de paciente encontrado no JSON!")

        except json.JSONDecodeError as e:
            print(f"[OCR]  Erro ao fazer parse do JSON: {e}")
            print(f"[OCR] Texto recebido: {texto_resposta}")
            return jsonify({
                "sucesso": 0,
                "erro": "Erro ao processar resposta do OCR",
                "detalhes": texto_resposta
            }), 500

        #  FALLBACK CRÃTICO: Se for pedido mÃ©dico e nÃ£o tiver exames, forÃ§ar extraÃ§Ã£o
        tipo_doc = dados_extraidos.get('tipo_documento', '')
        if tipo_doc == 'pedido_medico':
            if 'requisicao' not in dados_extraidos:
                dados_extraidos['requisicao'] = {}
            if 'itens_exame' not in dados_extraidos['requisicao'] or not dados_extraidos['requisicao']['itens_exame']:
                print(f"[OCR]  FALLBACK: Pedido mÃ©dico sem exames detectado! ForÃ§ando extraÃ§Ã£o...")
                # Tentar extrair exame dos dados clÃ­nicos ou usar genÃ©rico
                dados_clinicos_texto = dados_extraidos.get('requisicao', {}).get('dadosClinicos', {}).get('valor', '')

                # Lista de palavras-chave para identificar tipo de exame
                exame_fallback = "EXAME HISTOPATOLÃ“GICO"  # PadrÃ£o genÃ©rico

                if dados_clinicos_texto:
                    texto_upper = dados_clinicos_texto.upper()
                    if any(keyword in texto_upper for keyword in ['BIOPSIA', 'BIÃ“PSIA', 'HISTOPATOLOG', 'LESAO', 'LESÃƒO']):
                        exame_fallback = "HISTOPATOLÃ“GICO"
                    elif any(keyword in texto_upper for keyword in ['HEMOGRAMA', 'GLICEMIA', 'UREIA', 'CREATININA']):
                        exame_fallback = "MEDICINA LABORATORIAL"
                    elif any(keyword in texto_upper for keyword in ['CITOLOGIA', 'PAPANICO']):
                        exame_fallback = "COLPOCITOLOGIA"
                    elif any(keyword in texto_upper for keyword in ['PCR', 'COVID']):
                        exame_fallback = "PCR"

                dados_extraidos['requisicao']['itens_exame'] = [{
                    "descricao_ocr": exame_fallback,
                    "setor_sugerido": "anÃ¡tomo patolÃ³gico",
                    "fonte_extracao": "fallback_automatico"
                }]
                print(f"[OCR]  FALLBACK aplicado: Exame '{exame_fallback}' adicionado automaticamente")

        # CORREÃ‡ÃƒO AUTOMÃTICA DE PORTUGUÃŠS
        print(f"[OCR] Aplicando correÃ§Ã£o automÃ¡tica de portuguÃªs...")

        # Corrigir dados clÃ­nicos
        if 'requisicao' in dados_extraidos and isinstance(dados_extraidos['requisicao'], dict):
            if 'dadosClinicos' in dados_extraidos['requisicao'] and isinstance(dados_extraidos['requisicao']['dadosClinicos'], dict):
                texto_original = dados_extraidos['requisicao']['dadosClinicos'].get('valor', '')
                if texto_original and isinstance(texto_original, str):
                    texto_corrigido = corrigir_portugues(texto_original)
                    dados_extraidos['requisicao']['dadosClinicos']['valor'] = texto_corrigido
                    print(f"[OCR]  Dados clÃ­nicos corrigidos: {texto_corrigido[:50]}...")

            # Corrigir nomes dos exames
            if 'itens_exame' in dados_extraidos['requisicao'] and isinstance(dados_extraidos['requisicao']['itens_exame'], list):
                print(f"[OCR]  Encontrados {len(dados_extraidos['requisicao']['itens_exame'])} exames para corrigir")
                for idx, exame in enumerate(dados_extraidos['requisicao']['itens_exame']):
                    if isinstance(exame, dict) and 'descricao_ocr' in exame:
                        texto_original = exame['descricao_ocr']
                        if texto_original and isinstance(texto_original, str):
                            print(f"[OCR]  Corrigindo exame {idx+1}: '{texto_original}'")
                            texto_corrigido = corrigir_portugues(texto_original)
                            exame['descricao_ocr'] = texto_corrigido
                            exame['descricao_original'] = texto_original  # Manter original para referÃªncia
                            print(f"[OCR]  Exame {idx+1} corrigido: '{texto_corrigido}'")
                print(f"[OCR]  Todos os exames foram corrigidos")
            else:
                print(f"[OCR]  AVISO: Nenhum exame encontrado no campo itens_exame!")

        # NÃƒO remover campos null - retornar tudo que o Gemini extraiu
        print(f"[OCR] Retornando {len(dados_extraidos)} campos extraÃ­dos")

        # DEBUG: Mostrar se tem itens_exame
        if 'requisicao' in dados_extraidos and isinstance(dados_extraidos['requisicao'], dict):
            if 'itens_exame' in dados_extraidos['requisicao']:
                print(f"[OCR] âœ“ itens_exame encontrado: {dados_extraidos['requisicao']['itens_exame']}")
            else:
                print(f"[OCR] âš  itens_exame NÃƒO encontrado na requisicao!")
                print(f"[OCR] Campos disponÃ­veis em requisicao: {list(dados_extraidos['requisicao'].keys())}")

        # Log completo da resposta do Gemini para debug
        print(f"[OCR] === RESPOSTA COMPLETA DO GEMINI (primeiros 2000 chars) ===")
        print(texto_resposta[:2000])
        print(f"[OCR] ======================================================")

        # ðŸ†• BUSCAR ID DO PACIENTE PELO CPF (EVITAR DUPLICAÃ‡ÃƒO)
        id_paciente_existente = None
        if 'paciente' in dados_extraidos:
            paciente_data = dados_extraidos['paciente']
            
            # Extrair CPF (pode estar em diferentes formatos)
            cpf_extraido = None
            if 'NumCPF' in paciente_data:
                if isinstance(paciente_data['NumCPF'], dict):
                    cpf_extraido = paciente_data['NumCPF'].get('valor')
                else:
                    cpf_extraido = paciente_data['NumCPF']
            elif 'cpf' in paciente_data:
                cpf_extraido = paciente_data['cpf']
            
            if cpf_extraido:
                # Limpar CPF (remover pontos, traÃ§os, etc)
                cpf_limpo = ''.join(filter(str.isdigit, str(cpf_extraido)))
                
                if cpf_limpo and len(cpf_limpo) == 11:
                    logger.info(f"[OCR] ðŸ” Buscando paciente existente com CPF: {cpf_limpo}")
                    
                    # PASSO 1: Buscar no banco MySQL local
                    try:
                        connection = pymysql.connect(**DB_CONFIG)
                        with connection.cursor() as cursor:
                            query = "SELECT CodPaciente, NomPaciente FROM newdb.paciente WHERE CPF = %s LIMIT 1"
                            cursor.execute(query, (cpf_limpo,))
                            resultado = cursor.fetchone()
                            
                            if resultado:
                                id_paciente_existente = resultado[0]
                                nome_paciente_banco = resultado[1]
                                logger.info(f"[OCR] âœ… Paciente ENCONTRADO no banco LOCAL! ID: {id_paciente_existente} - {nome_paciente_banco}")
                                logger.info(f"[OCR] ðŸ’¡ Este ID serÃ¡ usado para evitar duplicaÃ§Ã£o")
                                
                                # Adicionar ID ao paciente nos dados extraÃ­dos
                                dados_extraidos['paciente']['IdPaciente'] = id_paciente_existente
                                dados_extraidos['paciente']['_paciente_existente'] = True
                                dados_extraidos['paciente']['_nome_banco'] = nome_paciente_banco
                                dados_extraidos['paciente']['_fonte_busca'] = 'banco_local'
                            else:
                                logger.info(f"[OCR] â„¹ï¸ Paciente com CPF {cpf_limpo} NÃƒO encontrado no banco local")
                        
                        connection.close()
                        
                    except Exception as e:
                        logger.error(f"[OCR] âš ï¸ Erro ao buscar paciente no banco local: {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    # PASSO 2: Se nÃ£o encontrou local, buscar na API do apLIS
                    if not id_paciente_existente:
                        logger.info(f"[OCR] ðŸ” Buscando paciente na API do apLIS pelo CPF...")
                        
                        try:
                            # Buscar paciente no apLIS usando pacienteListar
                            dat_busca = {
                                "cpf": cpf_limpo
                            }
                            
                            resposta_aplis = fazer_requisicao_aplis("pacienteListar", dat_busca)
                            
                            if resposta_aplis and resposta_aplis.get("dat", {}).get("sucesso") == 1:
                                lista_pacientes = resposta_aplis.get("dat", {}).get("lista", [])
                                
                                if lista_pacientes and len(lista_pacientes) > 0:
                                    # Paciente encontrado no apLIS!
                                    paciente_aplis = lista_pacientes[0]
                                    id_paciente_existente = paciente_aplis.get("CodPaciente") or paciente_aplis.get("IdPaciente") or paciente_aplis.get("idPaciente")
                                    nome_paciente_aplis = paciente_aplis.get("NomPaciente") or paciente_aplis.get("nomPaciente")
                                    
                                    logger.info(f"[OCR] âœ… Paciente ENCONTRADO na API do apLIS!")
                                    logger.info(f"[OCR]   ID: {id_paciente_existente}")
                                    logger.info(f"[OCR]   Nome: {nome_paciente_aplis}")
                                    logger.info(f"[OCR]   CPF: {cpf_limpo}")
                                    logger.info(f"[OCR] ðŸ’¡ Este ID serÃ¡ usado para evitar duplicaÃ§Ã£o")
                                    
                                    # Adicionar ID ao paciente nos dados extraÃ­dos
                                    dados_extraidos['paciente']['IdPaciente'] = id_paciente_existente
                                    dados_extraidos['paciente']['_paciente_existente'] = True
                                    dados_extraidos['paciente']['_nome_banco'] = nome_paciente_aplis
                                    dados_extraidos['paciente']['_fonte_busca'] = 'api_aplis'
                                else:
                                    logger.info(f"[OCR] â„¹ï¸ Paciente com CPF {cpf_limpo} NÃƒO encontrado na API do apLIS")
                                    logger.info(f"[OCR] ðŸ’¡ SerÃ¡ criado novo cadastro ao salvar")
                                    dados_extraidos['paciente']['_paciente_existente'] = False
                            else:
                                logger.warning(f"[OCR] âš ï¸ Erro ao buscar paciente no apLIS")
                                
                        except Exception as e:
                            logger.error(f"[OCR] âš ï¸ Erro ao buscar paciente no apLIS: {str(e)}")
                            logger.error(traceback.format_exc())
                            # Continuar mesmo com erro (nÃ£o bloquear o OCR)
                else:
                    logger.warning(f"[OCR] âš ï¸ CPF extraÃ­do invÃ¡lido: {cpf_extraido} (limpo: {cpf_limpo})")
            else:
                logger.warning(f"[OCR] âš ï¸ CPF nÃ£o encontrado nos dados extraÃ­dos do paciente")

        return jsonify({
            "sucesso": 1,
            "mensagem": "OCR processado com sucesso (portuguÃªs corrigido)",
            "dados": dados_extraidos,
            "id_paciente_existente": id_paciente_existente,  # ðŸ†• Retornar ID se encontrou
            "debug_resposta_gemini": texto_resposta[:10000]  # Aumentado para 1000 chars
        }), 200

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[OCR] âœ— Erro ao processar OCR: {str(e)}")
        logger.exception(f"[OCR] Stack trace:")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao processar OCR: {str(e)}",
            "traceback": tb
        }), 500


def corrigir_portugues(texto):
    """
    Corrige erros de portuguÃªs usando Vertex AI
    """
    if not texto or len(texto.strip()) < 3:
        return texto

    try:
        model = GenerativeModel("gemini-2.5-flash")

        prompt = f"""Corrija APENAS os erros de ortografia e gramÃ¡tica no texto abaixo.
Mantenha o significado original.
Retorne SOMENTE o texto corrigido, sem explicaÃ§Ãµes.

Texto: {texto}

Texto corrigido:"""

        response = model.generate_content(prompt)
        texto_corrigido = response.text.strip()

        print(f"[CORREÃ‡ÃƒO] Original: {texto}")
        print(f"[CORREÃ‡ÃƒO] Corrigido: {texto_corrigido}")

        return texto_corrigido
    except Exception as e:
        print(f"[CORREÃ‡ÃƒO] Erro ao corrigir: {e}")
        return texto  # Retorna original se falhar


# ============================================
# MAPEAMENTO COMPLETO DE TODOS OS EXAMES
# ============================================
MAPEAMENTO_EXAMES = {
    # MEDICINA LABORATORIAL - ID: 49
    'MEDICINA LABORATORIAL': 49,

    # CITOPATOLOGIA
    'BACTERIOSCOPIA': 50,
    'COLPOCITOLOGIA ONCÃ“TICA CONVENCIONAL': 20,
    'COLPOCITOLOGIA ONCÃ“TICA EM MEIO LÃQUIDO': 24,
    'CITOLOGIA HORMONAL ISOLADA': 21,
    'CITOLOGIA ONCÃ“TICA DE LÃQUIDOS': 4,
    'CITOLOGIA ANAL CONVENCIONAL': 33,
    'CITOLOGIA ANAL EM MEIO LIQUIDO': 34,
    'CITOLOGIA EM MEIO LÃQUIDO URINÃRIO': 35,
    'PROCEDIMENTO DIAGNÃ“STICO LÃ‚MINA DE PAAF ATÃ‰ 5': 36,
    'PUNÃ‡ÃƒO BIOPSIA ASPIRATIVA': 17,

    # ANÃTOMO PATOLÃ“GICO
    'BIÃ“PSIA SOE': 1,
    'BIOPSIA SOE': 1,
    'BIÃ“PSIA': 1,  # GenÃ©rico = SOE
    'BIÃ“PSIA': 1,  # GenÃ©rico = SOE
    'HISTOPATOLOGIA': 1,  # BiÃ³psia genÃ©rica
    'HISTOPATOLÃ“GICO': 1,
    'HISTOPATOLOGICO': 1,

    'PEÃ‡A CIRÃšRGICA SIMPLES': 2,
    'PECA CIRURGICA SIMPLES': 2,
    'PEÃ‡A CIRÃšRGICA COMPLEXA': 14,
    'PECA CIRURGICA COMPLEXA': 14,

    'BIÃ“PSIA SIMPLES': 23,
    'BIOPSIA SIMPLES': 23,
    'BIÃ“PSIA GÃSTRICA': 38,
    'BIOPSIA GASTRICA': 38,
    'BIÃ“PSIA DE MÃšLTIPLOS FRAGMENTOS': 40,
    'BIOPSIA DE MULTIPLOS FRAGMENTOS': 40,

    'NECRÃ“PSIA DE FETO': 43,
    'NECROPSIA DE FETO': 43,
    'EXAME PER-OPERATÃ“RIO POR CONGELAÃ‡ÃƒO': 3,

    # VARIAÃ‡Ã•ES COMUNS DE BIÃ“PSIAS
    'LESAO DE PELE': 23,  # BiÃ³psia simples
    'LESÃƒO DE PELE': 23,
    'LESAO': 23,
    'LESÃƒO': 23,
    'PELE': 23,
    'ABDOME': 23,
    'NODULO': 23,
    'NÃ“DULO': 23,
    'MAMA': 23,
    'TIREOIDE': 23,
    'TIROIDE': 23,

    # PCR
    'PCR': 51,
    'PCR EM TEMPO REAL DE HPV BAIXO/ALTO RISCO': 52,

    # REVISÃƒO
    'REVISÃƒO DE LÃ‚MINA INTERNA': 10,
    'REVISAO DE LAMINA INTERNA': 10,
    'REVISÃƒO DE LÃ‚MINA EXTERNO (BLOCO)': 11,
    'REVISAO DE LAMINA EXTERNO (BLOCO)': 11,
    'REVISÃƒO DE LÃ‚MINA EXTERNO (BLOCO + LÃ‚MINA)': 15,
    'REVISAO DE LAMINA EXTERNO (BLOCO + LAMINA)': 15,
    'REVISÃƒO DE LÃ‚MINA INTERNA - CITOLOGIA': 39,
    'REVISAO DE LAMINA INTERNA - CITOLOGIA': 39,

    # IMUNOISTOQUÃMICA
    'IMUNOISTOQUÃMICA INTERNA': 6,
    'IMUNOISTOQUIMICA INTERNA': 6,
    'IMUNOISTOQUÃMICA EXTERNA (BLOCO)': 12,
    'IMUNOISTOQUIMICA EXTERNA (BLOCO)': 12,
    'IMUNOISTOQUÃMICA EXTERNA (BLOCO+LÃ‚MINA)': 13,
    'IMUNOISTOQUIMICA EXTERNA (BLOCO+LAMINA)': 13,

    # EXAMES REALIZADOS POR PARCEIROS
    'CAPTURA HÃBRIDA': 22,
    'CAPTURA HIBRIDA': 22,

    # REDE APLIS
    'REDE - HISTOTÃ‰CNICA': 26,
    'REDE - HISTOTECNICA': 26,
    'REDE - MACROSCOPIA': 27,
    'REDE - MICROSCOPIA': 25,
    'REDE - IHQ': 28,
    'REDE - CITOPATOLOGIA': 30,
    'REDE - HIBRIDIZAÃ‡ÃƒO IN SITU': 31,
    'REDE - HIBRIDIZACAO IN SITU': 31,
    'REDE - PAT. CLINICA': 29,
    'REDE - IHQ + TECNICA': 41,
    'REDE - IHQ + TECNICA + MICRO': 42,

    # INTEGRAÃ‡ÃƒO
    'INTEGRAÃ‡ÃƒO': 18,
    'INTEGRACAO': 18,

    # FATURAMENTO EXTERNO
    'FAT. EXT. CAPTURA': 32,
    'FAT. EXT. CITO.': 46,
    'FAT. EXT. CONV.': 37,
    'FAT. EXT. CONV. + HORMONAL': 45,
    'FAT. EXT. PAINEL': 19,
    'SULA - FAT - EXAME LIBERADO NA REQUISIÃ‡ÃƒO DE CAPTURA HÃBRIDA': 47,
}


def identificar_tipo_exame_backend(nome):
    """
    Identifica o tipo de exame e retorna o ID correto baseado na lista completa de exames
    1. Tenta match exato no dicionÃ¡rio
    2. Tenta match parcial (contÃ©m)
    3. Usa categorizaÃ§Ã£o por palavras-chave para exames laboratoriais
    Retorna: (tipo_exame, cod_exame)
    """
    nome_upper = nome.upper().strip()

    # 1. TENTAR MATCH EXATO NO DICIONÃRIO
    if nome_upper in MAPEAMENTO_EXAMES:
        cod = MAPEAMENTO_EXAMES[nome_upper]
        return 'MATCH_EXATO', cod

    # 2. TENTAR MATCH PARCIAL (contÃ©m)
    for exame_nome, cod in MAPEAMENTO_EXAMES.items():
        # Se o nome do exame contÃ©m a palavra-chave OU vice-versa
        if exame_nome in nome_upper or nome_upper in exame_nome:
            return 'MATCH_PARCIAL', cod

    # 3. CATEGORIZAÃ‡ÃƒO POR PALAVRAS-CHAVE PARA MEDICINA LABORATORIAL
    medicina_lab_keywords = [
        'CREATININA', 'FERRITINA', 'FERRO', 'SÃ‰RICO', 'SERICO',
        'GAMA', 'GLUTAMIL', 'TRANSFERASE', 'GGT',
        'HEMOGLOBINA', 'GLICADA', 'HBA1C',
        'HEMOGRAMA', 'LEUCOGRAMA', 'PLAQUETAS', 'ERITROGRAMA',
        'LIPÃDICO', 'LIPIDICO', 'PERFIL', 'COLESTEROL', 'TRIGLICÃ‰RIDES', 'TRIGLICERIDES', 'HDL', 'LDL', 'VLDL',
        'TESTOSTERONA', 'BIODISPONÃVEL', 'BIODISPONIVEL', 'LIVRE', 'TOTAL',
        'TSH', 'TIREOTRÃ“FICO', 'TIREOTROPICO', 'TIREOESTIMULANTE', 'ULTRASSENSÃVEL', 'ULTRASSENSIVEL',
        'TIROXINA', 'T4', 'T3', 'TRIIODOTIRONINA',
        'TRANSAMINASE', 'OXALACÃ‰TICA', 'OXALACETICA', 'TGO', 'ASPARTATO', 'AMINO', 'AST',
        'PIRÃšVICA', 'PIRUVICA', 'TGP', 'ALANINA', 'ALT',
        'UREIA', 'UREICO', 'BUN',
        'VITAMINA', 'B12', 'COBALAMINA', 'D', 'HIDROXI', '25-HIDROXI', 'CALCIFEROL',
        'GLICOSE', 'GLICEMIA', 'JEJUM', 'PÃ“S', 'POS', 'PRANDIAL',
        'ÃCIDO', 'ACIDO', 'ÃšRICO', 'URICO',
        'CÃLCIO', 'CALCIO', 'IONICO', 'TOTAL',
        'FÃ“SFORO', 'FOSFORO', 'FOSFATO',
        'MAGNÃ‰SIO', 'MAGNESIO',
        'SÃ“DIO', 'SODIO', 'NA',
        'POTÃSSIO', 'POTASSIO', 'K',
        'CLORO', 'CL',
        'PROTEÃNA', 'PROTEINA',
        'ALBUMINA', 'SÃ‰RICA', 'SERICA',
        'GLOBULINA',
        'BILIRRUBINA', 'DIRETA', 'INDIRETA',
        'AMILASE', 'PANCREÃTICA', 'PANCREATICA',
        'LIPASE',
        'FOSFATASE', 'ALCALINA', 'FA',
        'DESIDROGENASE', 'LÃTICA', 'LATICA', 'LDH',
        'CPK', 'CREATINOQUINASE', 'MB', 'CK',
        'TROPONINA',
        'HORMÃ”NIO', 'HORMONIO',
        'ELETROFORESE', 'PROTEINOGRAMA',
        'PARATORMÃ”NIO', 'PARATORMONIO', 'PTH',
        'CORTISOL',
        'INSULINA',
        'PROLACTINA',
        'ESTRADIOL',
        'PROGESTERONA',
        'FSH', 'LH',
        'BETA', 'HCG',
        'PSA',
        'FERRITINA',
        'TRANSFERRINA',
        'VHS', 'VELOCIDADE', 'HEMOSSEDIMENTAÃ‡ÃƒO', 'HEMOSSEDIMENTACAO',
        'PCR', 'PROTEINA', 'C', 'REATIVA',
        'FATOR', 'REUMATOIDE',
        'ANTI', 'ANTICORPO'
    ]

    # 4. FALLBACK: CategorizaÃ§Ã£o por tipo de exame

    # BIÃ“PSIAS / HISTOPATOLOGIA (palavras-chave genÃ©ricas) â†’ BIÃ“PSIA SOE (ID: 1)
    biopsia_keywords = ['BIOPSIA', 'BIÃ“PSIA', 'HISTOPATOLOGIA', 'HISTOPATOLÃ“GICO',
                        'HISTOPATOLOGICO', 'LESAO', 'LESÃƒO', 'NODULO', 'NÃ“DULO']
    if any(keyword in nome_upper for keyword in biopsia_keywords):
        return 'ANÃTOMO PATOLÃ“GICO', 1

    # CITOPATOLOGIA (palavras-chave genÃ©ricas) â†’ Depende do tipo especÃ­fico
    cito_keywords = ['CITOLOGIA', 'CITOPATOLOGIA', 'COLPOCITOLOGIA', 'PAPANICOLAU',
                     'PREVENTIVO', 'ONCÃ“TICA', 'ONCOTICA']
    if any(keyword in nome_upper for keyword in cito_keywords):
        # Se tem "LIQUIDO" ou "LÃQUIDO", Ã© meio lÃ­quido (ID: 24)
        if 'LIQUIDO' in nome_upper or 'LÃQUIDO' in nome_upper:
            return 'CITOPATOLOGIA', 24
        # SenÃ£o Ã© convencional (ID: 20)
        return 'CITOPATOLOGIA', 20

    # MEDICINA LABORATORIAL (exames de sangue)
    if any(keyword in nome_upper for keyword in medicina_lab_keywords):
        return 'MEDICINA LABORATORIAL', 49

    # NÃ£o identificado
    return 'DESCONHECIDO', None


def buscar_dados_requisicao_simples(cod_requisicao):
    """
    Busca dados bÃ¡sicos de uma requisiÃ§Ã£o do apLIS (versÃ£o simplificada para consolidaÃ§Ã£o)

    Args:
        cod_requisicao: CÃ³digo da requisiÃ§Ã£o

    Returns:
        dict com dados bÃ¡sicos ou None se nÃ£o encontrar
    """
    try:
        logger.info(f"[BUSCA_SIMPLES] Buscando requisiÃ§Ã£o {cod_requisicao} do apLIS...")

        # Buscar nos Ãºltimos 365 dias
        hoje = datetime.now()
        periodo_fim = hoje.strftime("%Y-%m-%d")
        periodo_ini = (hoje - timedelta(days=365)).strftime("%Y-%m-%d")

        dat = {
            "ordenar": "IdRequisicao",
            "idEvento": "50",
            "periodoIni": periodo_ini,
            "periodoFim": periodo_fim,
            "pagina": 1,
            "tamanho": 100
        }

        resposta = fazer_requisicao_aplis("requisicaoListar", dat)

        if resposta.get("dat", {}).get("sucesso") != 1:
            logger.warning(f"[BUSCA_SIMPLES] Erro ao buscar: {resposta}")
            return None

        lista = resposta.get("dat", {}).get("lista", [])

        # Procurar requisiÃ§Ã£o especÃ­fica
        for req in lista:
            if req.get("CodRequisicao") == cod_requisicao:
                logger.info(f"[BUSCA_SIMPLES] âœ… RequisiÃ§Ã£o encontrada: {cod_requisicao}")

                # Retornar formato simplificado com dados do paciente
                return {
                    "requisicao": {
                        "codRequisicao": req.get("CodRequisicao"),
                        "dtaColeta": req.get("DtaColeta")
                    },
                    "paciente": {
                        "idPaciente": req.get("CodPaciente"),
                        "nome": req.get("NomPaciente"),
                        "cpf": req.get("CPF"),
                        "dtaNasc": req.get("DtaNascimento"),
                        "sexo": req.get("Sexo"),
                        "telCelular": req.get("TelCelular"),
                        "rg": req.get("RG"),
                        "email": req.get("Email"),
                        "endereco": {
                            "logradouro": req.get("Logradouro"),
                            "numEndereco": req.get("NumEndereco"),
                            "bairro": req.get("Bairro"),
                            "cidade": req.get("Cidade"),
                            "uf": req.get("UF"),
                            "cep": req.get("CEP")
                        }
                    }
                }

        logger.warning(f"[BUSCA_SIMPLES] âš ï¸ RequisiÃ§Ã£o {cod_requisicao} nÃ£o encontrada")
        return None

    except Exception as e:
        logger.error(f"[BUSCA_SIMPLES] Erro ao buscar requisiÃ§Ã£o: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


@app.route('/api/consolidar-resultados', methods=['POST'])
def consolidar_resultados():
    """
    Consolida todos os resultados de OCR no formato estruturado
    """
    try:
        dados = request.json
        resultados_ocr = dados.get('resultados_ocr', [])
        cod_requisicao = dados.get('codRequisicao')
        dados_api = dados.get('dados_api', {})  # Dados vindos da API (banco de dados)

        print(f"[CONSOLIDAR] Consolidando {len(resultados_ocr)} resultados OCR para requisiÃ§Ã£o {cod_requisicao}")
        print(f"[CONSOLIDAR] Dados da API recebidos: {bool(dados_api)}")

        # ðŸ†• BUSCAR REQUISIÃ‡Ã•ES MÃšLTIPLAS AUTOMATICAMENTE (0085 e 0200)
        codigos_encontrados = set()

        # Coletar TODOS os cÃ³digos de barras do OCR
        for resultado in resultados_ocr:
            dados_ocr = resultado.get('dados', {})
            comentarios = dados_ocr.get('comentarios_gerais', {})

            # CÃ³digo Ãºnico (retrocompatibilidade)
            if comentarios.get('requisicao_entrada'):
                codigos_encontrados.add(comentarios['requisicao_entrada'])

            # MÃºltiplos cÃ³digos (novo formato)
            if isinstance(comentarios.get('codigos_barras'), list):
                for codigo in comentarios['codigos_barras']:
                    if codigo and isinstance(codigo, str):
                        codigos_encontrados.add(codigo.strip())

        print(f"[CONSOLIDAR] ðŸ“Š CÃ³digos de barras encontrados no OCR: {codigos_encontrados}")

        # Se encontrou mÃºltiplos cÃ³digos E nÃ£o tem dados_api ainda, buscar todos
        if len(codigos_encontrados) > 1 and not dados_api:
            print(f"[CONSOLIDAR] ðŸ” Buscando automaticamente {len(codigos_encontrados)} requisiÃ§Ãµes...")

            requisicoes_buscadas = {}
            for codigo in codigos_encontrados:
                print(f"[CONSOLIDAR] ðŸ“ž Buscando requisiÃ§Ã£o: {codigo}")
                try:
                    # Buscar direto do apLIS usando a funÃ§Ã£o existente
                    # NOTA: Esta Ã© uma busca simples - a funÃ§Ã£o completa buscar_requisicao_integrada
                    # serÃ¡ chamada pelo frontend depois
                    dados_req = buscar_dados_requisicao_simples(codigo)

                    if dados_req and dados_req.get('paciente'):
                        requisicoes_buscadas[codigo] = dados_req
                        print(f"[CONSOLIDAR] âœ… RequisiÃ§Ã£o {codigo} encontrada!")
                    else:
                        print(f"[CONSOLIDAR] âš ï¸ RequisiÃ§Ã£o {codigo} nÃ£o encontrada ou sem dados de paciente")

                except Exception as e:
                    print(f"[CONSOLIDAR] âŒ Erro ao buscar requisiÃ§Ã£o {codigo}: {e}")
                    import traceback
                    print(f"[CONSOLIDAR] Traceback: {traceback.format_exc()}")

            # Escolher a requisiÃ§Ã£o com MAIS dados do paciente
            if requisicoes_buscadas:
                melhor_codigo = None
                melhor_score = 0

                for codigo, dados_req in requisicoes_buscadas.items():
                    paciente = dados_req.get('paciente', {})
                    # Score = quantidade de campos preenchidos
                    score = sum([
                        1 if paciente.get('nome') else 0,
                        1 if paciente.get('cpf') else 0,
                        1 if paciente.get('dtaNasc') else 0,
                        1 if paciente.get('rg') else 0,
                        1 if paciente.get('telCelular') else 0,
                        1 if paciente.get('email') else 0,
                        1 if paciente.get('endereco', {}).get('logradouro') else 0
                    ])
                    print(f"[CONSOLIDAR] ðŸ“ˆ Score de {codigo}: {score} campos preenchidos")

                    if score > melhor_score:
                        melhor_score = score
                        melhor_codigo = codigo

                if melhor_codigo:
                    dados_api = requisicoes_buscadas[melhor_codigo]
                    cod_requisicao = melhor_codigo
                    print(f"[CONSOLIDAR] ðŸ† Usando requisiÃ§Ã£o {melhor_codigo} (mais completa: {melhor_score} campos)")
                    print(f"[CONSOLIDAR] ðŸ“‹ Paciente: {dados_api.get('paciente', {}).get('nome')}")
            else:
                print(f"[CONSOLIDAR] âš ï¸ Nenhuma requisiÃ§Ã£o encontrada no apLIS")

        # Estrutura do JSON consolidado
        resultado_consolidado = {
            "metadata": {
                "timestamp_processamento": datetime.now().isoformat(),
                "total_requisicoes": 1,
                "versao_sistema": "2.0 - Sistema de AdmissÃ£o com OCR"
            },
            "requisicoes": [{
                "comentarios_gerais": {
                    "alertas_processamento": "Processamento automÃ¡tico via OCR",
                    "requisicao_entrada": cod_requisicao,
                    "idLocalOrigem": None,
                    "NomeLocalOrigem": None,
                    "arquivos_analisados": [],
                    "documentos_identificados": []
                },
                "paciente": {},
                "medico": {},
                "convenio": {},
                "requisicao": {},
                "amostras": {
                    "qtd_frascos_total": {"valor": None, "fonte": None, "confianca": None},
                    "tem_foto_frascos_juntos": {"valor": False, "fonte": None, "confianca": None},
                    "frascos_individuais": [],
                    "observacoes_frascos": {"valor": None, "fonte": None, "confianca": None}
                },
                "meta_dados_validacao": {
                    "validacao_identidade": {
                        "status": {"valor": None, "fonte": None, "confianca": None},
                        "acao_sistema": {
                            "mensagem": {"valor": None, "fonte": None, "confianca": None},
                            "tipo_acao": {"valor": None, "fonte": None, "confianca": None},
                            "destino": {"valor": None, "fonte": None, "confianca": None}
                        }
                    },
                    "completude_cadastral": {
                        "status": {"valor": None, "fonte": None, "confianca": None},
                        "acao_sistema": {
                            "mensagem": {"valor": None, "fonte": None, "confianca": None},
                            "tipo_acao": {"valor": None, "fonte": None, "confianca": None},
                            "destino": {"valor": None, "fonte": None, "confianca": None}
                        }
                    },
                    "codigo_barras_match": {
                        "status": {"valor": None, "fonte": None, "confianca": None},
                        "acao_sistema": {
                            "mensagem": {"valor": None, "fonte": None, "confianca": None},
                            "tipo_acao": {"valor": None, "fonte": None, "confianca": None},
                            "destino": {"valor": None, "fonte": None, "confianca": None}
                        }
                    },
                    "comprovante_pgto": {
                        "status": {"valor": None, "fonte": None, "confianca": None},
                        "acao_sistema": {
                            "mensagem": {"valor": None, "fonte": None, "confianca": None},
                            "tipo_acao": {"valor": None, "fonte": None, "confianca": None},
                            "destino": {"valor": None, "fonte": None, "confianca": None}
                        }
                    },
                    "meta_analise": {"valor": None, "fonte": None, "confianca": None}
                }
            }]
        }

        # Processar cada resultado de OCR
        for idx, resultado in enumerate(resultados_ocr):
            imagem_nome = resultado.get('imagem', '')
            dados_ocr = resultado.get('dados', {})

            print(f"[CONSOLIDAR] Processando resultado {idx+1}/{len(resultados_ocr)}")
            print(f"[CONSOLIDAR] Imagem: {imagem_nome}")
            print(f"[CONSOLIDAR] Dados OCR recebidos: {dados_ocr}")
            print(f"[CONSOLIDAR] Tipo dos dados: {type(dados_ocr)}")

            # Debug dos tipos internos
            if isinstance(dados_ocr, dict):
                for chave in ['paciente', 'medico', 'convenio', 'requisicao']:
                    if chave in dados_ocr:
                        print(f"[CONSOLIDAR] Tipo de '{chave}': {type(dados_ocr[chave])}")

            # Adicionar documento identificado
            resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["documentos_identificados"].append({
                "id_documento": f"doc_{idx+1}",
                "tipo_documento": dados_ocr.get('tipo_documento', 'outro'),
                "descricao": f"Imagem: {imagem_nome}"
            })

            resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["arquivos_analisados"].append(imagem_nome)

            # Mesclar dados do paciente - ðŸ†• MESCLAGEM INTELIGENTE (nÃ£o sobrescrever valores bons com null)
            if 'paciente' in dados_ocr and isinstance(dados_ocr['paciente'], dict):
                for key, value in dados_ocr['paciente'].items():
                    campo_atual = resultado_consolidado["requisicoes"][0]["paciente"].get(key)

                    # Extrair valores e confianÃ§a do novo dado
                    if isinstance(value, dict):
                        novo_valor = value.get('valor')
                        nova_confianca = value.get('confianca', 0)
                    else:
                        novo_valor = value
                        nova_confianca = 0

                    # Decidir se adiciona/sobrescreve
                    if campo_atual is None:
                        # Campo nÃ£o existe, adicionar
                        resultado_consolidado["requisicoes"][0]["paciente"][key] = value
                    elif isinstance(campo_atual, dict):
                        valor_atual = campo_atual.get('valor')
                        confianca_atual = campo_atual.get('confianca', 0)

                        # SÃ³ sobrescrever se o novo valor for melhor
                        if (valor_atual is None or valor_atual == '' or valor_atual == 'null') and novo_valor:
                            resultado_consolidado["requisicoes"][0]["paciente"][key] = value
                        elif nova_confianca > confianca_atual and novo_valor:
                            resultado_consolidado["requisicoes"][0]["paciente"][key] = value
                    else:
                        resultado_consolidado["requisicoes"][0]["paciente"][key] = value

                # ðŸ†• PÃ“S-PROCESSAMENTO: Verificar se DtaNascimento ou idade_formatada contÃ©m idade
                # e calcular a data de nascimento
                pac_consolidado = resultado_consolidado["requisicoes"][0]["paciente"]

                # Verificar campo DtaNascimento
                if 'DtaNascimento' in pac_consolidado:
                    dta_obj = pac_consolidado['DtaNascimento']
                    if isinstance(dta_obj, dict):
                        dta_valor = dta_obj.get('valor')
                        # Se contÃ©m "anos", Ã© idade formatada
                        if dta_valor and isinstance(dta_valor, str) and 'anos' in dta_valor.lower():
                            print(f"[CONSOLIDAR] ðŸŽ‚ OCR extraiu idade no campo DtaNascimento: {dta_valor}")
                            data_calculada = calcular_data_nascimento_por_idade(dta_valor)
                            if data_calculada:
                                pac_consolidado['DtaNascimento'] = {
                                    "valor": data_calculada,
                                    "fonte": f"Calculado de idade: {dta_valor}",
                                    "confianca": 0.85
                                }
                                print(f"[CONSOLIDAR] âœ… Data calculada: {data_calculada}")

                # Verificar campo idade_formatada (alternativo)
                if 'idade_formatada' in pac_consolidado:
                    idade_obj = pac_consolidado['idade_formatada']
                    if isinstance(idade_obj, dict):
                        idade_valor = idade_obj.get('valor')
                        if idade_valor and isinstance(idade_valor, str):
                            print(f"[CONSOLIDAR] ðŸŽ‚ OCR extraiu campo idade_formatada: {idade_valor}")
                            data_calculada = calcular_data_nascimento_por_idade(idade_valor)
                            if data_calculada:
                                # Criar ou atualizar DtaNascimento
                                pac_consolidado['DtaNascimento'] = {
                                    "valor": data_calculada,
                                    "fonte": f"Calculado de idade: {idade_valor}",
                                    "confianca": 0.85
                                }
                                print(f"[CONSOLIDAR] âœ… Data calculada de idade_formatada: {data_calculada}")
                                # Remover campo idade_formatada apÃ³s processamento
                                del pac_consolidado['idade_formatada']

            # Mesclar dados do mÃ©dico - ðŸ†• MESCLAGEM INTELIGENTE
            if 'medico' in dados_ocr and isinstance(dados_ocr['medico'], dict):
                for key, value in dados_ocr['medico'].items():
                    campo_atual = resultado_consolidado["requisicoes"][0]["medico"].get(key)

                    if isinstance(value, dict):
                        novo_valor = value.get('valor')
                        nova_confianca = value.get('confianca', 0)
                    else:
                        novo_valor = value
                        nova_confianca = 0

                    if campo_atual is None:
                        resultado_consolidado["requisicoes"][0]["medico"][key] = value
                    elif isinstance(campo_atual, dict):
                        valor_atual = campo_atual.get('valor')
                        confianca_atual = campo_atual.get('confianca', 0)

                        if (valor_atual is None or valor_atual == '' or valor_atual == 'null') and novo_valor:
                            resultado_consolidado["requisicoes"][0]["medico"][key] = value
                        elif nova_confianca > confianca_atual and novo_valor:
                            resultado_consolidado["requisicoes"][0]["medico"][key] = value
                    else:
                        resultado_consolidado["requisicoes"][0]["medico"][key] = value

            # Mesclar dados do convÃªnio - ðŸ†• MESCLAGEM INTELIGENTE
            if 'convenio' in dados_ocr and isinstance(dados_ocr['convenio'], dict):
                for key, value in dados_ocr['convenio'].items():
                    campo_atual = resultado_consolidado["requisicoes"][0]["convenio"].get(key)

                    if isinstance(value, dict):
                        novo_valor = value.get('valor')
                        nova_confianca = value.get('confianca', 0)
                    else:
                        novo_valor = value
                        nova_confianca = 0

                    if campo_atual is None:
                        resultado_consolidado["requisicoes"][0]["convenio"][key] = value
                    elif isinstance(campo_atual, dict):
                        valor_atual = campo_atual.get('valor')
                        confianca_atual = campo_atual.get('confianca', 0)

                        if (valor_atual is None or valor_atual == '' or valor_atual == 'null') and novo_valor:
                            resultado_consolidado["requisicoes"][0]["convenio"][key] = value
                        elif nova_confianca > confianca_atual and novo_valor:
                            resultado_consolidado["requisicoes"][0]["convenio"][key] = value
                    else:
                        resultado_consolidado["requisicoes"][0]["convenio"][key] = value

            # Mesclar dados da requisiÃ§Ã£o - INCLUIR TODOS OS CAMPOS (dict, list, str, etc)
            if 'requisicao' in dados_ocr and isinstance(dados_ocr['requisicao'], dict):
                tipo_doc = dados_ocr.get('tipo_documento', '')
                print(f"[CONSOLIDAR] ðŸ“‹ Processando requisiÃ§Ã£o da imagem: {imagem_nome}")
                print(f"[CONSOLIDAR] ðŸ“‹ Tipo de documento: {tipo_doc}")
                print(f"[CONSOLIDAR] ðŸ“‹ Campos em requisiÃ§Ã£o: {list(dados_ocr['requisicao'].keys())}")

                for key, value in dados_ocr['requisicao'].items():
                    print(f"[CONSOLIDAR]   Processando campo: {key}, tipo: {type(value)}")

                    # Para itens_exame, adicionar de pedido_medico OU laudo_medico
                    if key == 'itens_exame' and isinstance(value, list):
                        print(f"[CONSOLIDAR]   ðŸ”¬ Campo itens_exame encontrado! Tipo doc: {tipo_doc}, Qtd exames: {len(value)}")

                        # Adicionar exames de documentos tipo "pedido_medico" ou "laudo_medico"
                        if tipo_doc in ['pedido_medico', 'laudo_medico'] and len(value) > 0:
                            print(f"[CONSOLIDAR]   âœ“ Tipo de documento aceito: {tipo_doc}")

                            if key not in resultado_consolidado["requisicoes"][0]["requisicao"]:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key] = []
                                print(f"[CONSOLIDAR]   âœ“ Criado array vazio para itens_exame")

                            # Adicionar apenas se ainda nÃ£o tiver exames (evitar duplicatas)
                            if len(resultado_consolidado["requisicoes"][0]["requisicao"][key]) == 0:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key].extend(value)
                                print(f"[CONSOLIDAR]  âœ… Adicionados {len(value)} exames do {tipo_doc}: {imagem_nome}")
                            else:
                                print(f"[CONSOLIDAR]  âš ï¸ Ignorando exames duplicados da imagem: {imagem_nome}")
                        else:
                            print(f"[CONSOLIDAR]   âŒ Tipo de documento NÃƒO aceito ou array vazio: {tipo_doc}, len={len(value)}")
                    else:
                        # ðŸ†• MESCLAGEM INTELIGENTE para campos nÃ£o-exame
                        campo_atual = resultado_consolidado["requisicoes"][0]["requisicao"].get(key)

                        if isinstance(value, dict):
                            novo_valor = value.get('valor')
                            nova_confianca = value.get('confianca', 0)
                        else:
                            novo_valor = value
                            nova_confianca = 0

                        if campo_atual is None:
                            resultado_consolidado["requisicoes"][0]["requisicao"][key] = value
                        elif isinstance(campo_atual, dict):
                            valor_atual = campo_atual.get('valor')
                            confianca_atual = campo_atual.get('confianca', 0)

                            if (valor_atual is None or valor_atual == '' or valor_atual == 'null') and novo_valor:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key] = value
                            elif nova_confianca > confianca_atual and novo_valor:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key] = value
                        else:
                            resultado_consolidado["requisicoes"][0]["requisicao"][key] = value

        # ENRIQUECER ITENS_EXAME COM IDs DO BANCO DE DADOS
        if 'itens_exame' in resultado_consolidado["requisicoes"][0]["requisicao"]:
            itens_exame = resultado_consolidado["requisicoes"][0]["requisicao"]["itens_exame"]
            print(f"[CONSOLIDAR]  itens_exame encontrado: {itens_exame}")

            if isinstance(itens_exame, list) and len(itens_exame) > 0:
                print(f"[CONSOLIDAR] Enriquecendo {len(itens_exame)} exames com IDs do banco de dados...")

                # Extrair nomes dos exames
                nomes_exames = []
                for exame in itens_exame:
                    if isinstance(exame, dict):
                        nome = exame.get('descricao_ocr') or exame.get('descricao')
                        if nome:
                            nomes_exames.append(nome)
                    elif isinstance(exame, str):
                        nomes_exames.append(exame)

                if nomes_exames:
                    # Enriquecer exames usando mapeamento automÃ¡tico (sem banco de dados)
                    exames_enriquecidos = []
                    for idx, nome_exame in enumerate(nomes_exames):
                        nome_limpo = nome_exame.strip().upper()

                        # Identificar tipo de exame automaticamente POR CATEGORIA
                        tipo_identificado, cod_automatico = identificar_tipo_exame_backend(nome_limpo)

                        exame_enriquecido = {
                            "descricao_ocr": nome_exame,
                            "tipo_identificado": tipo_identificado
                        }

                        if cod_automatico:
                            # Mapeamento automÃ¡tico por categoria
                            exame_enriquecido["idExame"] = cod_automatico
                            exame_enriquecido["categoria"] = tipo_identificado
                            exame_enriquecido["encontrado"] = True
                            exame_enriquecido["mapeamento_automatico"] = True
                            print(f"[CONSOLIDAR]  {nome_exame} â†’ ID: {cod_automatico} ({tipo_identificado})")
                        else:
                            exame_enriquecido["encontrado"] = False
                            print(f"[CONSOLIDAR]  {nome_exame} nÃ£o identificado")

                        # Manter campos originais do OCR
                        if isinstance(itens_exame[idx], dict):
                            for k, v in itens_exame[idx].items():
                                if k not in exame_enriquecido:
                                    exame_enriquecido[k] = v

                        exames_enriquecidos.append(exame_enriquecido)

                    # Substituir lista original pela enriquecida
                    resultado_consolidado["requisicoes"][0]["requisicao"]["itens_exame"] = exames_enriquecidos
                    print(f"[CONSOLIDAR]  Exames enriquecidos com mapeamento automÃ¡tico (sem banco de dados)")
            else:
                print(f"[CONSOLIDAR]  AVISO: itens_exame estÃ¡ vazio ou nÃ£o Ã© uma lista vÃ¡lida!")
        else:
            print(f"[CONSOLIDAR]  AVISO: Campo itens_exame nÃ£o existe em requisicao!")

        # ADICIONAR DADOS DA API (BANCO DE DADOS) - com menor prioridade que OCR
        if dados_api:
            logger.info("[CONSOLIDAR] Adicionando dados da API ao resultado consolidado...")
            logger.debug(f"[CONSOLIDAR] Tipo de dados_api: {type(dados_api)}")
            logger.debug(f"[CONSOLIDAR] ConteÃºdo de dados_api: {dados_api}")

            # Verificar se dados_api Ã© um dicionÃ¡rio vÃ¡lido
            if not isinstance(dados_api, dict):
                logger.error(f"[CONSOLIDAR] ERRO: dados_api nÃ£o Ã© um dicionÃ¡rio, Ã© {type(dados_api)}")
                dados_api = {}  # Usar dicionÃ¡rio vazio para evitar erro

            # Se nÃ£o hÃ¡ resultados OCR, adicionar alerta
            if len(resultados_ocr) == 0:
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["alertas_processamento"] = "Dados extraÃ­dos apenas da API - Sem imagens para processar OCR"
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["arquivos_analisados"] = ["Nenhuma imagem processada"]
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["documentos_identificados"] = [{
                    "id_documento": "api_db",
                    "tipo_documento": "aplis",
                    "descricao": "Dados carregados do apLIS (sem OCR)"
                }]

            # Dados do Paciente da API
            if 'paciente' in dados_api and isinstance(dados_api['paciente'], dict):
                pac_api = dados_api['paciente']
                logger.debug(f"[CONSOLIDAR] Processando dados do paciente da API: {pac_api}")

                # ðŸ†• TODOS OS 16 CAMPOS DO PACIENTE (expandido para incluir todos os campos do banco)
                campos_paciente = {
                    'NomPaciente': pac_api.get('nome'),
                    'DtaNascimento': pac_api.get('dtaNasc'),
                    'sexo': pac_api.get('sexo'),
                    'cpf': pac_api.get('cpf'),
                    'RGNumero': pac_api.get('rg'),
                    'RGOrgao': pac_api.get('rgOrgao'),
                    'RGUF': pac_api.get('rgUF'),
                    'NomMae': pac_api.get('nomeMae'),
                    'EstadoCivil': pac_api.get('estadoCivil'),
                    'Passaporte': pac_api.get('passaporte'),
                    'MatConvenio': pac_api.get('matriculaConvenio'),
                    'ValidadeMatricula': pac_api.get('validadeMatricula'),
                    'telCelular': pac_api.get('telCelular'),
                    'telFixo': pac_api.get('telFixo'),
                    'email': pac_api.get('email')
                }

                for campo, valor in campos_paciente.items():
                    # ðŸ†• FALLBACK INTELIGENTE: Usar API se campo nÃ£o existe OU se existe mas estÃ¡ vazio
                    pac_ocr = resultado_consolidado["requisicoes"][0]["paciente"].get(campo)
                    campo_vazio_no_ocr = (pac_ocr is None or
                                         pac_ocr.get("valor") is None or
                                         pac_ocr.get("valor") == '' or
                                         pac_ocr.get("valor") == 'null')

                    # SÃ³ adicionar se:
                    # 1. Campo nÃ£o existe no OCR, OU
                    # 2. Campo existe no OCR mas estÃ¡ vazio
                    # E o valor da API nÃ£o Ã© None
                    if (campo not in resultado_consolidado["requisicoes"][0]["paciente"] or campo_vazio_no_ocr) and valor:
                        resultado_consolidado["requisicoes"][0]["paciente"][campo] = {
                            "valor": valor,
                            "fonte": "API/DB",
                            "confianca": 1.0
                        }
                        logger.debug(f"[CONSOLIDAR] âœ“ Adicionado (fallback): {campo} = {valor}")

                # ðŸ†• PROCESSAR DATA DE NASCIMENTO / IDADE FORMATADA
                # Se o campo DtaNascimento contÃ©m idade formatada ("48 anos 10 meses 10 dias"),
                # calcular a data de nascimento real
                if 'DtaNascimento' in resultado_consolidado["requisicoes"][0]["paciente"]:
                    dta_nasc_obj = resultado_consolidado["requisicoes"][0]["paciente"]['DtaNascimento']
                    if isinstance(dta_nasc_obj, dict):
                        dta_nasc_valor = dta_nasc_obj.get('valor')

                        # Verificar se Ã© idade formatada (contÃ©m "anos")
                        if dta_nasc_valor and isinstance(dta_nasc_valor, str) and 'anos' in dta_nasc_valor.lower():
                            logger.info(f"[CONSOLIDAR] ðŸŽ‚ Detectada idade formatada: {dta_nasc_valor}")

                            # Calcular data de nascimento a partir da idade
                            data_calculada = calcular_data_nascimento_por_idade(dta_nasc_valor)

                            if data_calculada:
                                # Atualizar com a data calculada
                                resultado_consolidado["requisicoes"][0]["paciente"]['DtaNascimento'] = {
                                    "valor": data_calculada,
                                    "fonte": f"Calculado de idade: {dta_nasc_valor}",
                                    "confianca": 0.85  # ConfianÃ§a um pouco menor pois Ã© calculado
                                }
                                logger.info(f"[CONSOLIDAR] âœ… Data de nascimento calculada: {data_calculada}")
                            else:
                                logger.warning(f"[CONSOLIDAR] âš ï¸ NÃ£o foi possÃ­vel calcular data de '{dta_nasc_valor}'")

                # EndereÃ§o do paciente - ðŸ†• COM FALLBACK INTELIGENTE
                if 'endereco' in pac_api and pac_api['endereco']:
                    end = pac_api['endereco']
                    if 'endereco' not in resultado_consolidado["requisicoes"][0]["paciente"]:
                        resultado_consolidado["requisicoes"][0]["paciente"]['endereco'] = {}

                    campos_endereco = {
                        'cep': end.get('cep'),
                        'logradouro': end.get('logradouro'),
                        'numEndereco': end.get('numEndereco'),
                        'complemento': end.get('complemento'),
                        'bairro': end.get('bairro'),
                        'cidade': end.get('cidade'),
                        'uf': end.get('uf')
                    }

                    for campo, valor in campos_endereco.items():
                        # ðŸ†• FALLBACK: Usar API se campo nÃ£o existe OU estÃ¡ vazio
                        end_ocr = resultado_consolidado["requisicoes"][0]["paciente"]['endereco'].get(campo)
                        campo_vazio_no_ocr = (end_ocr is None or
                                            end_ocr.get("valor") is None or
                                            end_ocr.get("valor") == '' or
                                            end_ocr.get("valor") == 'null')

                        if (campo not in resultado_consolidado["requisicoes"][0]["paciente"]['endereco'] or campo_vazio_no_ocr) and valor:
                            resultado_consolidado["requisicoes"][0]["paciente"]['endereco'][campo] = {
                                "valor": valor,
                                "fonte": "API/DB",
                                "confianca": 1.0
                            }
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de paciente na API")

            # Dados do MÃ©dico da API - ðŸ†• COM FALLBACK INTELIGENTE
            if 'medico' in dados_api and isinstance(dados_api['medico'], dict):
                med_api = dados_api['medico']
                logger.debug(f"[CONSOLIDAR] Processando dados do mÃ©dico da API: {med_api}")

                campos_medico = {
                    'NomMedico': med_api.get('nome'),
                    'numConselho': med_api.get('crm'),
                    'ufConselho': med_api.get('uf'),
                    'tipoConselho': 'CRM'
                }

                for campo, valor in campos_medico.items():
                    # ðŸ†• FALLBACK: Usar API se campo nÃ£o existe OU estÃ¡ vazio
                    med_ocr = resultado_consolidado["requisicoes"][0]["medico"].get(campo)
                    campo_vazio_no_ocr = (med_ocr is None or
                                         med_ocr.get("valor") is None or
                                         med_ocr.get("valor") == '' or
                                         med_ocr.get("valor") == 'null')

                    if (campo not in resultado_consolidado["requisicoes"][0]["medico"] or campo_vazio_no_ocr) and valor:
                        resultado_consolidado["requisicoes"][0]["medico"][campo] = {
                            "valor": valor,
                            "fonte": "API/DB",
                            "confianca": 1.0
                        }
                        logger.debug(f"[CONSOLIDAR] âœ“ Adicionado (fallback): {campo} = {valor}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de mÃ©dico na API")

            # Dados da RequisiÃ§Ã£o da API - ðŸ†• COM FALLBACK INTELIGENTE
            if 'requisicao' in dados_api and isinstance(dados_api['requisicao'], dict):
                req_api = dados_api['requisicao']
                logger.debug(f"[CONSOLIDAR] Processando dados da requisiÃ§Ã£o da API: {req_api}")

                campos_requisicao = {
                    'dtaColeta': req_api.get('dtaColeta'),
                    'dadosClinicos': req_api.get('dadosClinicos'),
                    'numGuia': req_api.get('numGuia')
                }

                for campo, valor in campos_requisicao.items():
                    # ðŸ†• FALLBACK: Usar API se campo nÃ£o existe OU estÃ¡ vazio
                    req_ocr = resultado_consolidado["requisicoes"][0]["requisicao"].get(campo)
                    campo_vazio_no_ocr = (req_ocr is None or
                                         req_ocr.get("valor") is None or
                                         req_ocr.get("valor") == '' or
                                         req_ocr.get("valor") == 'null')

                    if (campo not in resultado_consolidado["requisicoes"][0]["requisicao"] or campo_vazio_no_ocr) and valor:
                        resultado_consolidado["requisicoes"][0]["requisicao"][campo] = {
                            "valor": valor,
                            "fonte": "API/DB",
                            "confianca": 1.0
                        }
                        logger.debug(f"[CONSOLIDAR] âœ“ Adicionado (fallback): {campo} = {valor}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de requisiÃ§Ã£o na API")

            # ðŸ†• Dados do ConvÃªnio da API
            if 'convenio' in dados_api and isinstance(dados_api['convenio'], dict):
                conv_api = dados_api['convenio']
                logger.debug(f"[CONSOLIDAR] Processando dados do convÃªnio da API: {conv_api}")

                nome_convenio = conv_api.get('nome')
                # SÃ³ adicionar se tiver valor vÃ¡lido (nÃ£o fallback com "ConvÃªnio ID")
                if nome_convenio and not nome_convenio.startswith('ConvÃªnio ID'):
                    resultado_consolidado["requisicoes"][0]["convenio"]['nome'] = {
                        "valor": nome_convenio,
                        "fonte": "API/apLIS/CSV",
                        "confianca": 1.0
                    }
                    logger.debug(f"[CONSOLIDAR] âœ“ Adicionado convÃªnio: {nome_convenio}")
                else:
                    logger.debug(f"[CONSOLIDAR] ConvÃªnio sem dados vÃ¡lidos: {nome_convenio}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de convÃªnio na API")

            # ðŸ†• Dados da Fonte Pagadora da API
            if 'fontePagadora' in dados_api and isinstance(dados_api['fontePagadora'], dict):
                fonte_api = dados_api['fontePagadora']
                logger.debug(f"[CONSOLIDAR] Processando dados da fonte pagadora da API: {fonte_api}")

                nome_fonte = fonte_api.get('nome')
                # SÃ³ adicionar se tiver valor vÃ¡lido (nÃ£o fallback com "Local ID" ou "Fonte Pagadora ID")
                if nome_fonte and not nome_fonte.startswith('Local ID') and not nome_fonte.startswith('Fonte Pagadora ID'):
                    resultado_consolidado["requisicoes"][0]["fontePagadora"] = {
                        'nome': {
                            "valor": nome_fonte,
                            "fonte": "API/apLIS/CSV",
                            "confianca": 1.0
                        }
                    }
                    logger.debug(f"[CONSOLIDAR] âœ“ Adicionado fonte pagadora: {nome_fonte}")
                else:
                    logger.debug(f"[CONSOLIDAR] Fonte pagadora sem dados vÃ¡lidos: {nome_fonte}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de fonte pagadora na API")

            # ðŸ†• Dados do Local de Origem da API
            if 'localOrigem' in dados_api and isinstance(dados_api['localOrigem'], dict):
                local_api = dados_api['localOrigem']
                logger.debug(f"[CONSOLIDAR] Processando dados do local de origem da API: {local_api}")

                nome_local = local_api.get('nome')
                # SÃ³ adicionar se tiver valor vÃ¡lido (nÃ£o fallback com "Local ID")
                if nome_local and not nome_local.startswith('Local ID') and not nome_local.startswith('Local nÃ£o'):
                    resultado_consolidado["requisicoes"][0]["localOrigem"] = {
                        'nome': {
                            "valor": nome_local,
                            "fonte": "API/apLIS/CSV",
                            "confianca": 1.0
                        }
                    }
                    logger.debug(f"[CONSOLIDAR] âœ“ Adicionado local de origem: {nome_local}")

                    # TambÃ©m adicionar em comentarios_gerais
                    resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["NomeLocalOrigem"] = nome_local
                else:
                    logger.debug(f"[CONSOLIDAR] Local de origem sem dados vÃ¡lidos: {nome_local}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de local de origem na API")

            # ðŸ†• ADICIONAR STATUS APLIS (StatusExame)
            # Esse campo indica o status da requisiÃ§Ã£o no apLIS: 0=Em andamento, 1=ConcluÃ­do, 2=Cancelado
            if 'requisicao' in dados_api and isinstance(dados_api['requisicao'], dict):
                status_exame = dados_api['requisicao'].get('StatusExame')
                if status_exame is not None:
                    resultado_consolidado["requisicoes"][0]["StatusExame"] = status_exame
                    logger.debug(f"[CONSOLIDAR] âœ“ Adicionado StatusExame: {status_exame}")
            # Fallback: tentar diretamente do nÃ­vel superior
            elif 'StatusExame' in dados_api:
                status_exame = dados_api.get('StatusExame')
                if status_exame is not None:
                    resultado_consolidado["requisicoes"][0]["StatusExame"] = status_exame
                    logger.debug(f"[CONSOLIDAR] âœ“ Adicionado StatusExame (nivel superior): {status_exame}")

        # ðŸ†• SINCRONIZAÃ‡ÃƒO AUTOMÃTICA 0085 â†” 0200
        # Se detectou mÃºltiplos cÃ³digos na mesma imagem, criar requisiÃ§Ãµes duplicadas com dados idÃªnticos
        print(f"\n[CONSOLIDAR] ðŸ”„ Verificando sincronizaÃ§Ã£o 0085 â†” 0200...")
        print(f"[CONSOLIDAR] CÃ³digos encontrados: {codigos_encontrados}")

        # Identificar pares 0085/0200
        codigos_0085 = [c for c in codigos_encontrados if c.startswith('0085')]
        codigos_0200 = [c for c in codigos_encontrados if c.startswith('0200')]

        print(f"[CONSOLIDAR] RequisiÃ§Ãµes 0085: {codigos_0085}")
        print(f"[CONSOLIDAR] RequisiÃ§Ãµes 0200: {codigos_0200}")

        # Se encontrou AMBOS os tipos (0085 E 0200), criar requisiÃ§Ãµes duplicadas
        if len(codigos_0085) > 0 and len(codigos_0200) > 0:
            print(f"[CONSOLIDAR] âœ… Detectado par 0085/0200 na mesma imagem!")
            print(f"[CONSOLIDAR] ï¿½ï¿½ Criando requisiÃ§Ãµes sincronizadas com dados idÃªnticos...")

            # Pegar a requisiÃ§Ã£o consolidada como base
            requisicao_base = resultado_consolidado["requisicoes"][0].copy()

            # Criar lista de requisiÃ§Ãµes (uma para cada cÃ³digo)
            requisicoes_sincronizadas = []

            # Combinar todos os cÃ³digos encontrados
            todos_codigos = sorted(list(codigos_encontrados))

            for idx, codigo in enumerate(todos_codigos):
                # Fazer cÃ³pia profunda da requisiÃ§Ã£o base
                import copy
                req_sincronizada = copy.deepcopy(requisicao_base)

                # Atualizar o cÃ³digo da requisiÃ§Ã£o
                req_sincronizada["comentarios_gerais"]["requisicao_entrada"] = codigo

                # Adicionar metadata de sincronizaÃ§Ã£o
                req_sincronizada["comentarios_gerais"]["sincronizacao_0085_0200"] = {
                    "sincronizado": True,
                    "tipo_requisicao": "0085" if codigo.startswith('0085') else "0200",
                    "par_encontrado": todos_codigos,
                    "dados_identicos": True,
                    "fonte_sincronizacao": "OCR - Mesma imagem"
                }

                requisicoes_sincronizadas.append(req_sincronizada)
                print(f"[CONSOLIDAR]   âœ“ RequisiÃ§Ã£o {idx+1}/{len(todos_codigos)}: {codigo}")

            # Substituir array de requisiÃ§Ãµes
            resultado_consolidado["requisicoes"] = requisicoes_sincronizadas
            resultado_consolidado["metadata"]["total_requisicoes"] = len(requisicoes_sincronizadas)

            print(f"[CONSOLIDAR] âœ… Criadas {len(requisicoes_sincronizadas)} requisiÃ§Ãµes sincronizadas")
            print(f"[CONSOLIDAR] ðŸŽ¯ Dados de paciente, mÃ©dico e convÃªnio sÃ£o IDÃŠNTICOS em todas")
        else:
            print(f"[CONSOLIDAR] â„¹ï¸ Apenas um tipo de requisiÃ§Ã£o detectado (sem sincronizaÃ§Ã£o)")

        # LOG FINAL - Mostrar resumo do que foi consolidado
        print(f"\n[CONSOLIDAR] ===== RESUMO DA CONSOLIDAÃ‡ÃƒO =====")
        print(f"[CONSOLIDAR] Total de imagens processadas: {len(resultados_ocr)}")
        print(f"[CONSOLIDAR] Dados da API incluÃ­dos: {bool(dados_api)}")
        print(f"[CONSOLIDAR] Total de requisiÃ§Ãµes geradas: {len(resultado_consolidado['requisicoes'])}")

        for idx, req in enumerate(resultado_consolidado['requisicoes']):
            cod_req = req["comentarios_gerais"].get("requisicao_entrada", "N/A")
            print(f"[CONSOLIDAR] --- RequisiÃ§Ã£o {idx+1}: {cod_req} ---")
            print(f"[CONSOLIDAR]   Campos no paciente: {len(req['paciente'])}")
            print(f"[CONSOLIDAR]   Campos no medico: {len(req['medico'])}")
            print(f"[CONSOLIDAR]   Campos no convenio: {len(req['convenio'])}")
            print(f"[CONSOLIDAR]   Campos na requisicao: {len(req['requisicao'])}")

        print(f"[CONSOLIDAR] =====================================\n")

        # ðŸ†• SALVAR AUTOMATICAMENTE NO SUPABASE - TODAS AS REQUISIÃ‡Ã•ES SINCRONIZADAS
        print(f"[CONSOLIDAR] ðŸ” Debug Supabase:")
        print(f"[CONSOLIDAR]   - SUPABASE_ENABLED: {SUPABASE_ENABLED}")
        print(f"[CONSOLIDAR]   - Total de requisiÃ§Ãµes para salvar: {len(resultado_consolidado['requisicoes'])}")
        print(f"[CONSOLIDAR]   - supabase_manager: {supabase_manager is not None}")

        if SUPABASE_ENABLED and len(resultado_consolidado['requisicoes']) > 0:
            try:
                # Salvar TODAS as requisiÃ§Ãµes (0085 e 0200 se houver sincronizaÃ§Ã£o)
                for idx, req_dados in enumerate(resultado_consolidado['requisicoes']):
                    cod_req = req_dados["comentarios_gerais"].get("requisicao_entrada")

                    if not cod_req:
                        print(f"[CONSOLIDAR] âš ï¸ RequisiÃ§Ã£o {idx+1} sem cÃ³digo, pulando...")
                        continue

                    print(f"[CONSOLIDAR] ðŸ’¾ Salvando requisiÃ§Ã£o {idx+1}/{len(resultado_consolidado['requisicoes'])}: {cod_req}")

                    # Dados do paciente (simplificados para campos indexados)
                    paciente_data = {}
                    if 'paciente' in req_dados:
                        pac = req_dados['paciente']
                        # Extrair valores dos campos {valor, fonte, confianca}
                        for key, val in pac.items():
                            if isinstance(val, dict) and 'valor' in val:
                                paciente_data[key] = val['valor']
                            else:
                                paciente_data[key] = val

                    # Extrair lista de exames
                    exames_list = []
                    exames_ids = []
                    if 'requisicao' in req_dados and 'itens_exame' in req_dados['requisicao']:
                        for item in req_dados['requisicao']['itens_exame']:
                            if isinstance(item, dict):
                                desc = item.get('descricao_ocr') or item.get('descricao_original') or str(item)
                                exames_list.append(desc)
                                if 'idExame' in item:
                                    exames_ids.append(item['idExame'])
                            else:
                                exames_list.append(str(item))

                    # Salvar no Supabase
                    resultado_save = supabase_manager.salvar_requisicao(
                        cod_requisicao=cod_req,
                        dados_paciente=paciente_data,
                        dados_ocr={"resultados": resultados_ocr},  # Salvar OCR bruto
                        dados_consolidados=req_dados,  # Salvar dados especÃ­ficos desta requisiÃ§Ã£o
                        exames=exames_list,
                        exames_ids=exames_ids,
                        processado_por='sistema_ocr'
                    )

                    if resultado_save.get('sucesso') == 1:
                        print(f"[CONSOLIDAR] âœ… RequisiÃ§Ã£o {cod_req} salva no Supabase! (AÃ§Ã£o: {resultado_save.get('acao')})")
                    else:
                        print(f"[CONSOLIDAR] âš ï¸ Erro ao salvar requisiÃ§Ã£o {cod_req}: {resultado_save.get('erro')}")

                print(f"[CONSOLIDAR] âœ… Finalizado salvamento de {len(resultado_consolidado['requisicoes'])} requisiÃ§Ãµes")

            except Exception as e:
                # NÃ£o quebrar o fluxo se der erro no Supabase
                print(f"[CONSOLIDAR] âš ï¸ Erro ao salvar no Supabase (continuando): {str(e)}")
                import traceback
                print(traceback.format_exc())

        return jsonify({
            "sucesso": 1,
            "resultado": resultado_consolidado
        }), 200

    except Exception as e:
        print(f"[CONSOLIDAR] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao consolidar resultados: {str(e)}"
        }), 500


@app.route('/api/exames/buscar-por-nome', methods=['POST'])
def buscar_exames_por_nome():
    """
    Busca IDs de exames no banco de dados a partir dos nomes extraÃ­dos pelo OCR
    """
    try:
        dados = request.get_json()
        nomes_exames = dados.get('nomes_exames', [])

        if not nomes_exames or not isinstance(nomes_exames, list):
            return jsonify({
                "sucesso": 0,
                "erro": "nomes_exames deve ser um array de strings"
            }), 400

        print(f"[BUSCAR EXAMES] Buscando IDs para {len(nomes_exames)} exames...")

        resultados = []

        for nome_exame in nomes_exames:
            nome_limpo = nome_exame.strip().upper()
            print(f"[BUSCAR EXAMES] Procurando: {nome_limpo}")

            # Identificar tipo de exame usando a funÃ§Ã£o global (baseado em categorias)
            tipo_identificado, cod_automatico = identificar_tipo_exame_backend(nome_limpo)
            print(f"[BUSCAR EXAMES] Tipo identificado: {tipo_identificado} (CodExame: {cod_automatico})")

            # Usar mapeamento automÃ¡tico por categoria
            if cod_automatico:
                resultados.append({
                    "nome_ocr": nome_exame,
                    "idExame": cod_automatico,
                    "NomExame": tipo_identificado,
                    "categoria": tipo_identificado,
                    "tipo_identificado": tipo_identificado,
                    "encontrado": True,
                    "mapeamento_automatico": True,
                    "alternativas": []
                })
                print(f"[BUSCAR EXAMES]  Mapeado por categoria: {nome_exame} â†’ ID: {cod_automatico} ({tipo_identificado})")
            else:
                resultados.append({
                    "nome_ocr": nome_exame,
                    "idExame": None,
                    "tipo_identificado": tipo_identificado,
                    "encontrado": False,
                    "mensagem": f"Exame '{nome_exame}' nÃ£o identificado por categoria"
                })
                print(f"[BUSCAR EXAMES]  NÃ£o identificado: {nome_exame} (categoria: {tipo_identificado})")

        # Contar quantos foram encontrados
        encontrados = sum(1 for r in resultados if r['encontrado'])

        # Gerar string de IDs para o campo EXAMES CONVÃŠNIO (separados por vÃ­rgula)
        ids_encontrados = [str(r['idExame']) for r in resultados if r['encontrado'] and r['idExame']]
        ids_string = ", ".join(ids_encontrados)

        # Gerar string de nomes para registro/visualizaÃ§Ã£o
        nomes_encontrados = [r['nome_ocr'] for r in resultados if r['encontrado']]
        nomes_string = ", ".join(nomes_encontrados)

        print(f"[BUSCAR EXAMES] IDs encontrados: {ids_string}")
        print(f"[BUSCAR EXAMES] Nomes dos exames: {nomes_string}")

        return jsonify({
            "sucesso": 1,
            "total_solicitado": len(nomes_exames),
            "total_encontrado": encontrados,
            "ids_string": ids_string,  # String pronta para campo "EXAMES CONVÃŠNIO"
            "nomes_string": nomes_string,  # String com nomes dos exames para registro
            "resultados": resultados
        }), 200

    except Exception as e:
        print(f"[BUSCAR EXAMES] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar exames: {str(e)}"
        }), 500


def limpar_imagens_temporarias():
    """
    Limpa todas as imagens temporÃ¡rias ao iniciar o servidor
    """
    try:
        if os.path.exists(TEMP_IMAGES_DIR):
            import shutil
            shutil.rmtree(TEMP_IMAGES_DIR)
            os.makedirs(TEMP_IMAGES_DIR, exist_ok=True)
            print(f"[OK] Diretorio de imagens temporarias limpo: {TEMP_IMAGES_DIR}")
    except Exception as e:
        print(f"[AVISO] Erro ao limpar imagens temporarias: {e}")


# ========================================
# ENDPOINTS DE CONSULTA AOS CSVs
# ========================================

@app.route('/api/medicos', methods=['GET'])
def listar_medicos():
    """Lista todos os mÃ©dicos do CSV"""
    try:
        medicos_lista = list(MEDICOS_CACHE.values())
        return jsonify({
            "sucesso": 1,
            "total": len(medicos_lista),
            "medicos": medicos_lista
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar mÃ©dicos: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/medicos/<crm>/<uf>', methods=['GET'])
def buscar_medico(crm, uf):
    """Busca mÃ©dico por CRM e UF"""
    try:
        medico = buscar_medico_por_crm(crm, uf.upper())
        if medico:
            return jsonify({
                "sucesso": 1,
                "medico": medico
            }), 200
        else:
            return jsonify({
                "sucesso": 0,
                "erro": f"MÃ©dico CRM {crm}/{uf} nÃ£o encontrado"
            }), 404
    except Exception as e:
        logger.error(f"[API] Erro ao buscar mÃ©dico: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/convenios', methods=['GET'])
def listar_convenios():
    """Lista todos os convÃªnios do CSV"""
    try:
        convenios_lista = list(CONVENIOS_CACHE.values())
        return jsonify({
            "sucesso": 1,
            "total": len(convenios_lista),
            "convenios": convenios_lista
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar convÃªnios: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/convenios/<id_convenio>', methods=['GET'])
def buscar_convenio_endpoint(id_convenio):
    """Busca convênio por ID"""
    try:
        convenio = buscar_convenio_por_id(id_convenio)
        if convenio:
            return jsonify({
                "sucesso": 1,
                "convenio": convenio
            }), 200
        else:
            return jsonify({
                "sucesso": 0,
                "erro": f"Convênio ID {id_convenio} não encontrado"
            }), 404
    except Exception as e:
        logger.error(f"[API] Erro ao buscar convênio: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/locais-origem', methods=['GET'])
def listar_locais_origem():
    """
    Lista locais de origem: clinicas/hospitais que enviam exames.
    Sao registros de fatinstituicao com Local = 1 e Inativo = 0.
    Consulta o banco diretamente para garantir dados sempre atualizados,
    separados dos convenios (planos de saude).
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)
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
        logger.error(f"[API] Erro ao listar locais de origem: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/fontes-pagadoras', methods=['GET'])
def listar_fontes_pagadoras():
    """
    Lista fontes pagadoras: entidades que PAGAM pelos exames.
    Sao registros de fatinstituicao com FontePagadora = 1 e Inativo = 0.
    Diferentes de convenios (fatconvenio) e de locais de origem (Local=1).
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT
                IdInstituicao AS id,
                NomFantasia   AS nome
            FROM newdb.fatinstituicao
            WHERE FontePagadora = 1
              AND Inativo = 0
              AND NomFantasia IS NOT NULL
              AND NomFantasia != ''
            ORDER BY NomFantasia ASC
        """)
        fontes = cursor.fetchall()
        cursor.close()
        connection.close()

        return jsonify({
            "sucesso": 1,
            "total": len(fontes),
            "fontes": fontes
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar fontes pagadoras: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/instituicoes', methods=['GET'])
def listar_instituicoes():
    """Lista todas as instituiÃ§Ãµes do CSV"""
    try:
        instituicoes_lista = list(INSTITUICOES_CACHE.values())
        return jsonify({
            "sucesso": 1,
            "total": len(instituicoes_lista),
            "instituicoes": instituicoes_lista
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar instituiÃ§Ãµes: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/instituicoes/<id_instituicao>', methods=['GET'])
def buscar_instituicao_endpoint(id_instituicao):
    """Busca instituiÃ§Ã£o por ID"""
    try:
        instituicao = buscar_instituicao_por_id(id_instituicao)
        if instituicao:
            return jsonify({
                "sucesso": 1,
                "instituicao": instituicao
            }), 200
        else:
            return jsonify({
                "sucesso": 0,
                "erro": f"InstituiÃ§Ã£o ID {id_instituicao} nÃ£o encontrada"
            }), 404
    except Exception as e:
        logger.error(f"[API] Erro ao buscar instituiÃ§Ã£o: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500




# ============================================
# ROTAS DO SUPABASE - HISTÃ“RICO DE REQUISIÃ‡Ã•ES
# ============================================

@app.route('/api/historico/salvar', methods=['POST'])
def salvar_requisicao_historico():
    """
    Salva uma requisiÃ§Ã£o processada no histÃ³rico (Supabase)

    Body:
        - cod_requisicao (obrigatÃ³rio)
        - dados_paciente (obrigatÃ³rio)
        - dados_ocr (opcional)
        - dados_consolidados (opcional)
        - exames (opcional): lista de nomes
        - exames_ids (opcional): lista de IDs
    """
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase nÃ£o estÃ¡ configurado"
        }), 503

    try:
        dados = request.json

        if not dados.get('cod_requisicao'):
            return jsonify({
                "sucesso": 0,
                "erro": "CÃ³digo da requisiÃ§Ã£o Ã© obrigatÃ³rio"
            }), 400

        if not dados.get('dados_paciente'):
            return jsonify({
                "sucesso": 0,
                "erro": "Dados do paciente sÃ£o obrigatÃ³rios"
            }), 400

        resultado = supabase_manager.salvar_requisicao(
            cod_requisicao=dados['cod_requisicao'],
            dados_paciente=dados['dados_paciente'],
            dados_ocr=dados.get('dados_ocr'),
            dados_consolidados=dados.get('dados_consolidados'),
            exames=dados.get('exames'),
            exames_ids=dados.get('exames_ids'),
            processado_por=dados.get('processado_por', 'sistema')
        )

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500

    except Exception as e:
        logger.error(f"[HISTORICO] Erro ao salvar: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500

@app.route('/api/historico/<cod_requisicao>', methods=['GET'])
def buscar_requisicao_historico(cod_requisicao):
    """Busca uma requisiÃ§Ã£o especÃ­fica no histÃ³rico"""
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase nÃ£o estÃ¡ configurado"
        }), 503

    try:
        resultado = supabase_manager.buscar_requisicao(cod_requisicao)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 404

    except Exception as e:
        logger.error(f"[HISTORICO] Erro ao buscar: {e}")
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500

@app.route('/api/historico/listar', methods=['GET'])
def listar_requisicoes_historico():
    """Lista requisiÃ§Ãµes recentes do histÃ³rico"""
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase nÃ£o estÃ¡ configurado"
        }), 503

    try:
        limite = request.args.get('limite', 50, type=int)

        resultado = supabase_manager.listar_requisicoes_recentes(limite)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500

    except Exception as e:
        logger.error(f"[HISTORICO] Erro ao listar: {e}")
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500

@app.route('/api/historico/buscar-cpf/<cpf>', methods=['GET'])
def buscar_por_cpf_historico(cpf):
    """Busca requisiÃ§Ãµes por CPF do paciente"""
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase nÃ£o estÃ¡ configurado"
        }), 503

    try:
        resultado = supabase_manager.buscar_por_cpf(cpf)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500

    except Exception as e:
        logger.error(f"[HISTORICO] Erro ao buscar por CPF: {e}")
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500

@app.route('/api/paciente/buscar-por-cpf', methods=['POST'])
def buscar_paciente_por_cpf():
    """
    DEPRECATED: Use /api/buscar-paciente ao invÃ©s desta rota
    Busca paciente no banco de dados MySQL pelo CPF
    Retorna o CodPaciente e dados bÃ¡sicos do paciente
    """
    return buscar_paciente()  # Redireciona para a nova funÃ§Ã£o


@app.route('/api/buscar-paciente', methods=['POST'])
def buscar_paciente():
    """
    Busca paciente no banco de dados MySQL e na API do apLIS pelo CPF ou Nome Completo
    
    FLUXO DE BUSCA:
    1. Busca no banco MySQL local (mais rÃ¡pido)
    2. Se nÃ£o encontrar, busca na API do apLIS
    
    Aceita: { "cpf": "12345678900" } OU { "nome": "Kaua Larsson Lopes de Sousa" }
    Retorna o CodPaciente e dados completos do paciente
    """
    try:
        dados = request.get_json()
        cpf = dados.get('cpf')
        nome = dados.get('nome')

        if not cpf and not nome:
            return jsonify({
                "sucesso": 0,
                "erro": "CPF ou Nome nÃ£o fornecido"
            }), 400

        # ETAPA 1: BUSCAR NO BANCO MYSQL LOCAL
        paciente_encontrado = False
        
        try:
            connection = pymysql.connect(**DB_CONFIG)
            if not connection:
                logger.error(f"[BUSCAR_PACIENTE] âŒ Erro ao conectar no banco de dados")
            else:
                try:
                    with connection.cursor() as cursor:
                        # Buscar por CPF
                        if cpf:
                            cpf_limpo = ''.join(filter(str.isdigit, cpf))
                            logger.info(f"[BUSCAR_PACIENTE] ðŸ” Buscando no banco LOCAL com CPF: {cpf_limpo}")
                            
                            query = """
                                SELECT 
                                    CodPaciente,
                                    NomPaciente,
                                    CPF,
                                    DtaNascimento,
                                    RGNumero,
                                    Sexo
                                FROM newdb.paciente
                                WHERE CPF = %s
                                LIMIT 1
                            """
                            cursor.execute(query, (cpf_limpo,))
                        
                        # Buscar por Nome Completo
                        elif nome:
                            nome_limpo = nome.strip().lower()
                            logger.info(f"[BUSCAR_PACIENTE] ðŸ” Buscando no banco LOCAL com Nome: {nome_limpo}")
                            
                            query = """
                                SELECT 
                                    CodPaciente,
                                    NomPaciente,
                                    CPF,
                                    DtaNascimento,
                                    RGNumero,
                                    Sexo
                                FROM newdb.paciente
                                WHERE LOWER(NomPaciente) = %s
                                LIMIT 1
                            """
                            cursor.execute(query, (nome_limpo,))

                        resultado = cursor.fetchone()

                        if resultado:
                            cod_paciente = resultado[0]
                            nome_paciente = resultado[1]
                            cpf_db = resultado[2]
                            dta_nasc = resultado[3]
                            rg = resultado[4]
                            sexo = resultado[5]

                            logger.info(f"[BUSCAR_PACIENTE] âœ… Paciente encontrado no banco LOCAL!")
                            logger.info(f"[BUSCAR_PACIENTE]   CodPaciente: {cod_paciente}")
                            logger.info(f"[BUSCAR_PACIENTE]   Nome: {nome_paciente}")
                            logger.info(f"[BUSCAR_PACIENTE]   CPF: {cpf_db}")

                            # Buscar dados completos do paciente
                            dados_completos = buscar_dados_completos_paciente(cod_paciente)

                            paciente_encontrado = True
                            
                            return jsonify({
                                "sucesso": 1,
                                "fonte": "banco_local",
                                "paciente": {
                                    "idPaciente": cod_paciente,
                                    "nome": nome_paciente,
                                    "cpf": cpf_db if cpf_db else None,
                                    "dataNascimento": dta_nasc.isoformat() if dta_nasc else None,
                                    "rg": rg,
                                    "sexo": sexo,
                                    "dadosCompletos": dados_completos
                                }
                            }), 200

                finally:
                    connection.close()
        
        except Exception as e:
            logger.error(f"[BUSCAR_PACIENTE] âš ï¸ Erro ao buscar no banco local: {str(e)}")
        
        # ETAPA 2: SE NÃƒO ENCONTROU LOCAL, BUSCAR NA API DO apLIS
        if not paciente_encontrado and cpf:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            logger.info(f"[BUSCAR_PACIENTE] ðŸ” Paciente nÃ£o encontrado localmente, buscando na API do apLIS...")
            
            try:
                # Buscar paciente no apLIS usando pacienteListar
                dat_busca = {
                    "cpf": cpf_limpo
                }
                
                resposta_aplis = fazer_requisicao_aplis("pacienteListar", dat_busca)
                
                if resposta_aplis and resposta_aplis.get("dat", {}).get("sucesso") == 1:
                    lista_pacientes = resposta_aplis.get("dat", {}).get("lista", [])
                    
                    if lista_pacientes and len(lista_pacientes) > 0:
                        # Paciente encontrado no apLIS!
                        paciente_aplis = lista_pacientes[0]
                        id_paciente = paciente_aplis.get("CodPaciente") or paciente_aplis.get("IdPaciente") or paciente_aplis.get("idPaciente")
                        nome_paciente = paciente_aplis.get("NomPaciente") or paciente_aplis.get("nomPaciente")
                        cpf_aplis = paciente_aplis.get("CPF") or paciente_aplis.get("cpf")
                        dta_nasc = paciente_aplis.get("DtaNascimento") or paciente_aplis.get("dtaNascimento")
                        rg = paciente_aplis.get("RG") or paciente_aplis.get("rg")
                        sexo = paciente_aplis.get("Sexo") or paciente_aplis.get("sexo")
                        
                        logger.info(f"[BUSCAR_PACIENTE] âœ… Paciente encontrado na API do apLIS!")
                        logger.info(f"[BUSCAR_PACIENTE]   ID: {id_paciente}")
                        logger.info(f"[BUSCAR_PACIENTE]   Nome: {nome_paciente}")
                        logger.info(f"[BUSCAR_PACIENTE]   CPF: {cpf_aplis}")
                        
                        return jsonify({
                            "sucesso": 1,
                            "fonte": "api_aplis",
                            "paciente": {
                                "idPaciente": id_paciente,
                                "nome": nome_paciente,
                                "cpf": cpf_aplis,
                                "dataNascimento": dta_nasc,
                                "rg": rg,
                                "sexo": sexo,
                                "dadosCompletos": paciente_aplis
                            }
                        }), 200
            
            except Exception as e:
                logger.error(f"[BUSCAR_PACIENTE] âš ï¸ Erro ao buscar no apLIS: {str(e)}")
                logger.error(traceback.format_exc())
        
        # NÃƒO ENCONTROU EM NENHUM LUGAR
        criterio = f"CPF {cpf_limpo if cpf else ''}" if cpf else f"Nome '{nome}'"
        logger.warning(f"[BUSCAR_PACIENTE] âš ï¸ Paciente com {criterio} nÃ£o encontrado em nenhum sistema")
        return jsonify({
            "sucesso": 0,
            "erro": f"Paciente com {criterio} nÃ£o encontrado no sistema"
        }), 404

    except Exception as e:
        logger.error(f"[BUSCAR_PACIENTE] âŒ ExceÃ§Ã£o: {str(e)}")
        import traceback
        logger.error(f"[BUSCAR_PACIENTE] Traceback: {traceback.format_exc()}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar paciente: {str(e)}"
        }), 500


@app.route('/api/paciente/criar', methods=['POST'])
def criar_paciente():
    """
    Cria um novo paciente no sistema
    Valida CPF pela Receita Federal antes de criar
    Verifica duplicidade de CPF
    """
    try:
        dados = request.get_json()
        logger.info(f"[CRIAR_PACIENTE] Dados recebidos: {dados}")

        # Validar campos obrigatÃ³rios
        nome = dados.get('nome')
        cpf = dados.get('cpf')
        data_nascimento = dados.get('dataNascimento') or dados.get('dtaNasc')

        if not nome:
            return jsonify({
                "sucesso": 0,
                "erro": "Nome do paciente Ã© obrigatÃ³rio"
            }), 400

        if not cpf:
            return jsonify({
                "sucesso": 0,
                "erro": "CPF Ã© obrigatÃ³rio para criar novo paciente"
            }), 400

        # Limpar CPF
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_limpo) != 11:
            return jsonify({
                "sucesso": 0,
                "erro": "CPF invÃ¡lido (deve ter 11 dÃ­gitos)"
            }), 400

        logger.info(f"[CRIAR_PACIENTE] Verificando se CPF {cpf_limpo} jÃ¡ existe no banco...")

        # 1. VERIFICAR SE JÃ EXISTE PACIENTE COM ESTE CPF
        try:
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                query = "SELECT CodPaciente, NomPaciente FROM newdb.paciente WHERE CPF = %s LIMIT 1"
                cursor.execute(query, (cpf_limpo,))
                resultado = cursor.fetchone()

                if resultado:
                    cod_paciente_existente = resultado[0]
                    nome_existente = resultado[1]
                    logger.warning(f"[CRIAR_PACIENTE] âš ï¸ Paciente com CPF {cpf_limpo} jÃ¡ existe: ID {cod_paciente_existente} - {nome_existente}")
                    connection.close()
                    return jsonify({
                        "sucesso": 0,
                        "erro": f"Paciente com este CPF jÃ¡ cadastrado: {nome_existente} (ID: {cod_paciente_existente})",
                        "paciente_existente": {
                            "idPaciente": cod_paciente_existente,
                            "nome": nome_existente,
                            "cpf": cpf_limpo
                        }
                    }), 409  # 409 Conflict

            connection.close()
        except Exception as e:
            logger.error(f"[CRIAR_PACIENTE] Erro ao verificar duplicidade: {str(e)}")
            return jsonify({
                "sucesso": 0,
                "erro": f"Erro ao verificar duplicidade de CPF: {str(e)}"
            }), 500

        # 2. VALIDAR CPF NA RECEITA FEDERAL
        logger.info(f"[CRIAR_PACIENTE] ðŸ” Validando CPF {cpf_limpo} na Receita Federal...")
        dados_receita = consultar_cpf_receita_federal(cpf_limpo, data_nascimento)

        usa_metodo_sem_cpf = False
        
        if not dados_receita or not dados_receita.get('valido'):
            logger.warning(f"[CRIAR_PACIENTE] âš ï¸ CPF {cpf_limpo} nÃ£o validado pela Receita Federal")
            logger.info(f"[CRIAR_PACIENTE] ðŸ”„ Usando mÃ©todo alternativo: Paciente sem documento (CPF nÃ£o validado)")
            usa_metodo_sem_cpf = True
        else:
            logger.info(f"[CRIAR_PACIENTE] âœ… CPF validado pela Receita Federal!")
            logger.info(f"[CRIAR_PACIENTE]   Nome na RF: {dados_receita.get('nome')}")
            logger.info(f"[CRIAR_PACIENTE]   Data Nasc: {dados_receita.get('data_nascimento')}")

        # 3. CRIAR PACIENTE NO apLIS
        if usa_metodo_sem_cpf:
            logger.info(f"[CRIAR_PACIENTE] ðŸ“ Criando paciente com mÃ©todo 'Sem Documento'...")
            logger.warning(f"[CRIAR_PACIENTE] âš ï¸ ATENÃ‡ÃƒO: CPF {cpf_limpo} NÃƒO FOI VALIDADO na Receita Federal")
        else:
            logger.info(f"[CRIAR_PACIENTE] ðŸ“ Criando paciente no apLIS...")

        # Montar estrutura para o apLIS
        dat = {
            "idEvento": "3",  # Evento de inclusÃ£o de paciente
            "nome": nome
        }
        
        # Se CPF foi validado, enviar CPF. Se nÃ£o, usar cpfAusente
        if usa_metodo_sem_cpf:
            dat["cpfAusente"] = "1"  # Paciente sem documento
            logger.warning(f"[CRIAR_PACIENTE] âš ï¸ CPF {cpf_limpo} nÃ£o validado - usando cpfAusente")
        else:
            dat["cpf"] = cpf_limpo

        # Adicionar campos opcionais se fornecidos
        if data_nascimento:
            # Converter para formato do apLIS se necessÃ¡rio
            if 'T' in data_nascimento:
                data_nascimento = data_nascimento.split('T')[0]
            dat['dtaNascimento'] = data_nascimento
        elif dados_receita and dados_receita.get('data_nascimento'):
            # Usar data da Receita Federal (sÃ³ se validou)
            dat['dtaNascimento'] = dados_receita['data_nascimento']

        if dados.get('rg'):
            dat['rg'] = dados['rg']
        if dados.get('telefone') or dados.get('telCelular'):
            dat['telefone'] = dados.get('telefone') or dados.get('telCelular')
        if dados.get('email'):
            dat['email'] = dados['email']
        if dados.get('sexo'):
            dat['sexo'] = dados['sexo']
        if dados.get('endereco'):
            dat['endereco'] = dados['endereco']

        logger.info(f"[CRIAR_PACIENTE] Chamando apLIS com dados: {dat}")

        # Chamar o apLIS para criar paciente
        resposta = fazer_requisicao_aplis("pacienteSalvar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            cod_paciente = resposta.get("dat", {}).get("codPaciente")
            logger.info(f"[CRIAR_PACIENTE] âœ… Paciente criado com sucesso! CodPaciente: {cod_paciente}")

            # ðŸ†• VERIFICAR SE NÃƒO HOUVE DUPLICAÃ‡ÃƒO (verificaÃ§Ã£o adicional de seguranÃ§a)
            if not usa_metodo_sem_cpf and cpf_limpo:
                try:
                    logger.info(f"[CRIAR_PACIENTE] ðŸ” VERIFICANDO se houve duplicaÃ§Ã£o do paciente (CPF: {cpf_limpo})...")

                    # Buscar todos os pacientes com este CPF no apLIS
                    dat_verificacao = {"cpf": cpf_limpo}
                    resposta_verificacao = fazer_requisicao_aplis("pacienteListar", dat_verificacao)

                    if resposta_verificacao and resposta_verificacao.get("dat", {}).get("sucesso") == 1:
                        lista_encontrada = resposta_verificacao.get("dat", {}).get("lista", [])
                        quantidade = len(lista_encontrada)

                        if quantidade == 1:
                            logger.info(f"[CRIAR_PACIENTE] âœ… VERIFICAÃ‡ÃƒO OK: Apenas 1 paciente com CPF {cpf_limpo}")
                            logger.info(f"[CRIAR_PACIENTE]   ID confirmado: {lista_encontrada[0].get('CodPaciente')}")
                        elif quantidade > 1:
                            logger.error(f"[CRIAR_PACIENTE] âŒâŒâŒ DUPLICAÃ‡ÃƒO DETECTADA! âŒâŒâŒ")
                            logger.error(f"[CRIAR_PACIENTE]   CPF: {cpf_limpo}")
                            logger.error(f"[CRIAR_PACIENTE]   Quantidade de pacientes encontrados: {quantidade}")
                            logger.error(f"[CRIAR_PACIENTE]   IDs duplicados: {[p.get('CodPaciente') for p in lista_encontrada]}")
                            logger.error(f"[CRIAR_PACIENTE]   âš ï¸ AÃ‡ÃƒO NECESSÃRIA: Verificar e remover duplicatas no sistema apLIS!")

                            # Logar detalhes de cada paciente duplicado
                            for idx, pac in enumerate(lista_encontrada, 1):
                                logger.error(f"[CRIAR_PACIENTE]   Paciente {idx}: ID={pac.get('CodPaciente')}, Nome={pac.get('NomPaciente')}")
                        else:
                            logger.warning(f"[CRIAR_PACIENTE] âš ï¸ ALERTA: Busca nÃ£o retornou nenhum paciente (esperado 1)")
                    else:
                        logger.warning(f"[CRIAR_PACIENTE] âš ï¸ NÃ£o foi possÃ­vel verificar duplicaÃ§Ã£o: {resposta_verificacao}")

                except Exception as e_verif:
                    logger.error(f"[CRIAR_PACIENTE] âš ï¸ Erro ao verificar duplicaÃ§Ã£o (nÃ£o crÃ­tico): {str(e_verif)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # NÃ£o interromper o fluxo

            # ðŸ†• SALVAR PACIENTE NO BANCO LOCAL para evitar duplicaÃ§Ã£o futura
            try:
                logger.info(f"[CRIAR_PACIENTE] ðŸ’¾ Salvando paciente no banco LOCAL para prevenir duplicaÃ§Ã£o...")
                connection = pymysql.connect(**DB_CONFIG)
                with connection.cursor() as cursor:
                    query_insert = """
                        INSERT INTO newdb.paciente
                        (CodPaciente, NomPaciente, CPF, DtaNasc, NumRG, TelCelular, DscEndereco, Email)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            NomPaciente = VALUES(NomPaciente),
                            CPF = VALUES(CPF),
                            DtaNasc = VALUES(DtaNasc),
                            NumRG = VALUES(NumRG),
                            TelCelular = VALUES(TelCelular),
                            DscEndereco = VALUES(DscEndereco),
                            Email = VALUES(Email)
                    """

                    cursor.execute(query_insert, (
                        cod_paciente,
                        nome,
                        cpf_limpo if not usa_metodo_sem_cpf else None,
                        dat.get('dtaNascimento') or data_nascimento,
                        dados.get('rg'),
                        dados.get('telefone') or dados.get('telCelular'),
                        dados.get('endereco'),
                        dados.get('email')
                    ))
                    connection.commit()
                    logger.info(f"[CRIAR_PACIENTE] âœ… Paciente {cod_paciente} salvo no banco LOCAL com sucesso!")
                connection.close()
            except Exception as e_local:
                logger.error(f"[CRIAR_PACIENTE] âš ï¸ Erro ao salvar no banco local (nÃ£o crÃ­tico): {str(e_local)}")
                # NÃ£o interromper o fluxo se falhar ao salvar no local

            resposta_final = {
                "sucesso": 1,
                "mensagem": "Paciente criado com sucesso",
                "paciente": {
                    "idPaciente": cod_paciente,
                    "nome": nome,
                    "cpf": cpf_limpo,
                    "dataNascimento": dat.get('dtaNascimento'),
                    "validado_receita": not usa_metodo_sem_cpf,
                    "nome_receita": dados_receita.get('nome') if dados_receita else None
                }
            }
            
            # Adicionar aviso se usou mÃ©todo alternativo
            if usa_metodo_sem_cpf:
                resposta_final["aviso"] = {
                    "tipo": "cpf_nao_validado",
                    "mensagem": f"âš ï¸ ATENÃ‡ÃƒO: Paciente cadastrado com mÃ©todo alternativo (CPF {cpf_limpo} nÃ£o foi validado na Receita Federal). Verifique os dados do paciente.",
                    "cpf": cpf_limpo
                }
                logger.warning(f"[CRIAR_PACIENTE] âš ï¸ Retornando aviso de CPF nÃ£o validado: {cpf_limpo}")
            
            return jsonify(resposta_final), 201
        else:
            erro_msg = resposta.get("dat", {}).get("msg", "Erro desconhecido")
            logger.error(f"[CRIAR_PACIENTE] âŒ Erro ao criar paciente: {erro_msg}")
            return jsonify({
                "sucesso": 0,
                "erro": f"Erro ao criar paciente no sistema: {erro_msg}"
            }), 400

    except Exception as e:
        logger.error(f"[CRIAR_PACIENTE] Erro: {e}")
        import traceback
        logger.error(f"[CRIAR_PACIENTE] Traceback: {traceback.format_exc()}")
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500


@app.route('/api/paciente/<id_paciente>', methods=['PUT'])
def atualizar_paciente(id_paciente):
    """Atualiza dados de um paciente"""
    try:
        dados = request.get_json()
        logger.info(f"[ATUALIZAR_PACIENTE] ID: {id_paciente}, Dados: {dados}")

        # Montar estrutura para o apLIS
        dat = {
            "idEvento": "4",  # Evento de alteraÃ§Ã£o de paciente
            "codPaciente": id_paciente
        }

        # Adicionar campos que foram enviados
        if dados.get('nome'):
            dat['nomePaciente'] = dados['nome']
        if dados.get('dtaNasc'):
            dat['dtaNascimento'] = dados['dtaNasc']
        if dados.get('cpf'):
            dat['cpf'] = dados['cpf']
        if dados.get('rg'):
            dat['rg'] = dados['rg']
        if dados.get('telCelular'):
            dat['telefone'] = dados['telCelular']
        if dados.get('email'):
            dat['email'] = dados['email']
        if dados.get('matriculaConvenio'):
            dat['matriculaConvenio'] = dados['matriculaConvenio']
        if dados.get('numGuia'):
            # SÃ³ envia se for vÃ¡lido: 9 dÃ­gitos e nÃ£o sÃ³ zeros
            num_guia = str(dados['numGuia']).strip()
            num_guia_limpo = ''.join(filter(str.isdigit, num_guia))
            
            if num_guia_limpo and len(num_guia_limpo) == 9 and num_guia_limpo != '000000000':
                dat['numGuiaConvenio'] = num_guia_limpo
                logger.info(f"[ATUALIZAR_PACIENTE] âœ… numGuia vÃ¡lido, serÃ¡ enviado: {num_guia_limpo}")
            else:
                logger.info(f"[ATUALIZAR_PACIENTE] â„¹ï¸ numGuia invÃ¡lido ('{num_guia_limpo}'), nÃ£o serÃ¡ enviado")
        if dados.get('endereco'):
            dat['endereco'] = dados['endereco']

        logger.info(f"[ATUALIZAR_PACIENTE] Chamando apLIS com dados: {dat}")

        # Chamar o apLIS para atualizar
        resposta = fazer_requisicao_aplis("pacienteAlterar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            logger.info(f"[ATUALIZAR_PACIENTE] âœ… Paciente atualizado com sucesso")
            return jsonify({
                "sucesso": 1,
                "mensagem": "Dados do paciente atualizados com sucesso"
            }), 200
        else:
            erro_msg = resposta.get("dat", {}).get("msg", "Erro desconhecido")
            logger.error(f"[ATUALIZAR_PACIENTE] âŒ Erro: {erro_msg}")
            return jsonify({
                "sucesso": 0,
                "erro": erro_msg
            }), 400

    except Exception as e:
        logger.error(f"[ATUALIZAR_PACIENTE] Erro: {e}")
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500

@app.route('/api/requisicao/<cod_requisicao>', methods=['PUT'])
def atualizar_requisicao(cod_requisicao):
    """Atualiza dados de uma requisiÃ§Ã£o"""
    try:
        dados = request.get_json()
        logger.info(f"[ATUALIZAR_REQUISICAO] CÃ³digo: {cod_requisicao}, Dados: {dados}")

        # Montar estrutura para o apLIS
        dat = {
            "idEvento": "51",  # Evento de alteraÃ§Ã£o de requisiÃ§Ã£o
            "codRequisicao": cod_requisicao
        }

        # Adicionar campos que foram enviados
        if dados.get('dtaColeta'):
            dat['dtaColeta'] = dados['dtaColeta']
        if dados.get('convenio'):
            dat['nomeConvenio'] = dados['convenio']
        if dados.get('origem'):
            dat['nomeOrigem'] = dados['origem']
        if dados.get('fontePagadora'):
            dat['nomeFontePagadora'] = dados['fontePagadora']
        if dados.get('medico'):
            dat['nomeMedico'] = dados['medico']
        if dados.get('crm'):
            dat['crm'] = dados['crm']
        if dados.get('numGuia'):
            # SÃ³ envia se for vÃ¡lido: 9 dÃ­gitos e nÃ£o sÃ³ zeros
            num_guia = str(dados['numGuia']).strip()
            num_guia_limpo = ''.join(filter(str.isdigit, num_guia))
            
            if num_guia_limpo and len(num_guia_limpo) == 9 and num_guia_limpo != '000000000':
                dat['numGuia'] = num_guia_limpo
                logger.info(f"[ATUALIZAR_REQUISICAO] âœ… numGuia vÃ¡lido, serÃ¡ enviado: {num_guia_limpo}")
            else:
                logger.info(f"[ATUALIZAR_REQUISICAO] â„¹ï¸ numGuia invÃ¡lido ('{num_guia_limpo}'), nÃ£o serÃ¡ enviado")
        if dados.get('dadosClinicos'):
            dat['dadosClinicos'] = dados['dadosClinicos']

        logger.info(f"[ATUALIZAR_REQUISICAO] Chamando apLIS com dados: {dat}")

        # Chamar o apLIS para atualizar
        resposta = fazer_requisicao_aplis("requisicaoAlterar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            logger.info(f"[ATUALIZAR_REQUISICAO] âœ… RequisiÃ§Ã£o atualizada com sucesso")
            return jsonify({
                "sucesso": 1,
                "mensagem": "Dados da requisiÃ§Ã£o atualizados com sucesso"
            }), 200
        else:
            erro_msg = resposta.get("dat", {}).get("msg", "Erro desconhecido")
            logger.error(f"[ATUALIZAR_REQUISICAO] âŒ Erro: {erro_msg}")
            return jsonify({
                "sucesso": 0,
                "erro": erro_msg
            }), 400

    except Exception as e:
        logger.error(f"[ATUALIZAR_REQUISICAO] Erro: {e}")
        return jsonify({
            "sucesso": 0,
            "erro": str(e)
        }), 500


# ============================================================================
# ROTAS DE WEBHOOK - WhatsApp/WAHA Integration
# ============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def webhook_principal():
    """
    Endpoint principal de webhook para integraÃ§Ã£o com WhatsApp/WAHA.
    Por enquanto apenas registra os eventos recebidos.
    """
    try:
        if request.method == 'GET':
            # Responder a verificaÃ§Ãµes de webhook (challenge)
            return jsonify({"status": "ok", "message": "Webhook ativo"}), 200
        
        # POST - processar evento do webhook
        dados = request.get_json()
        logger.info(f"[WEBHOOK] Evento recebido: {dados.get('event', 'desconhecido')}")
        
        # Por enquanto apenas confirma recebimento
        # TODO: Implementar lÃ³gica de processamento de mensagens WhatsApp
        return jsonify({"status": "ok", "message": "Evento recebido"}), 200
        
    except Exception as e:
        logger.error(f"[WEBHOOK] Erro ao processar webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/<path:subpath>', methods=['POST', 'GET'])
def webhook_subpath(subpath):
    """
    Endpoint genÃ©rico para webhooks com subpaths (ex: /webhook/LabWahaPlus).
    Redireciona para o handler principal.
    """
    try:
        if request.method == 'GET':
            return jsonify({"status": "ok", "message": f"Webhook ativo: {subpath}"}), 200
        
        dados = request.get_json()
        logger.info(f"[WEBHOOK/{subpath}] Evento recebido: {dados.get('event', 'desconhecido')}")
        
        # Por enquanto apenas confirma recebimento
        return jsonify({"status": "ok", "message": "Evento recebido"}), 200
        
    except Exception as e:
        logger.error(f"[WEBHOOK/{subpath}] Erro: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# REGISTRAR ROTAS DE DROPDOWNS
# ========================================
try:
    from rotas_dropdowns import registrar_rotas
    registrar_rotas(app, logger, DB_CONFIG, CONVENIOS_CACHE)
except Exception as e:
    logger.error(f"[ERRO] Falha ao registrar rotas de dropdowns: {e}")

if __name__ == '__main__':
    # Limpar imagens temporÃ¡rias ao iniciar
    limpar_imagens_temporarias()

    logger.info("=" * 80)
    logger.info("API DE ADMISSAO - BACKEND INICIANDO")
    logger.info("=" * 80)
    logger.info(f"Servidor local: http://localhost:5000")
    logger.info(f"Servidor publico: http://0.0.0.0:5000")
    logger.info("")
    logger.info("DICA: Se estiver usando ngrok, configure assim:")
    logger.info("   Terminal 1: python api_admissao.py")
    logger.info("   Terminal 2: ngrok http 5000")
    logger.info("")
    logger.info(f"Diretorio de logs: {LOG_DIR}")
    logger.info(f"Diretorio de imagens temporarias: {TEMP_IMAGES_DIR}")
    logger.info("")
    logger.info("Endpoints disponiveis:")
    logger.info("  GET  /api/health                 - Status do servidor")
    logger.info("  GET  /api/admissao/teste         - Testar conexao com apLIS")
    logger.info("  POST /api/requisicoes/listar     - Listar requisicoes (nova metodologia)")
    logger.info("  GET  /api/requisicao/<cod>       - Buscar requisicao com dados e imagens")
    logger.info("  GET  /api/imagem/<filename>      - Servir imagem temporaria")
    logger.info("  POST /api/admissao/salvar        - Salvar admissao")
    logger.info("  POST /api/admissao/validar       - Validar dados")
    logger.info("  POST /api/ocr/processar          - Processar OCR em imagem")
    logger.info("  POST /api/consolidar-resultados  - Consolidar resultados OCR")
    logger.info("  POST /api/exames/buscar-por-nome - Buscar IDs de exames")
    logger.info("  POST /api/buscar-paciente        - Buscar paciente por CPF ou nome")
    logger.info("  POST /api/paciente/criar         - Criar novo paciente (valida CPF na Receita)")
    logger.info("  PUT  /api/paciente/<id>          - Atualizar dados de paciente")
    logger.info("  GET  /api/medicos                - Listar todos os mÃ©dicos (CSV)")
    logger.info("  GET  /api/medicos/<crm>/<uf>     - Buscar mÃ©dico por CRM/UF")
    logger.info("  GET  /api/convenios              - Listar todos os convÃªnios (CSV)")
    logger.info("  GET  /api/convenios/<id>         - Buscar convÃªnio por ID")
    logger.info("  GET  /api/instituicoes           - Listar todas as instituiÃ§Ãµes (CSV)")
    logger.info("  GET  /api/instituicoes/<id>      - Buscar instituiÃ§Ã£o por ID")
    logger.info("")
    logger.info("METODOLOGIA ATUALIZADA:")
    logger.info("  - Usando fazer_requisicao_aplis() para todas as chamadas ao apLIS")
    logger.info("  - Suporte a requisicaoListar para listagem de requisiÃ§Ãµes")
    logger.info("  - Logging detalhado de todas as requisiÃ§Ãµes e respostas")
    logger.info("  - CriaÃ§Ã£o automÃ¡tica de pacientes com validaÃ§Ã£o CPF na Receita Federal")
    logger.info("")
    logger.info("CORS configurado para aceitar requisiÃ§Ãµes de qualquer origem")
    logger.info("URLs dinamicas habilitadas (funciona com localhost e ngrok)")
    logger.info("Logging completo habilitado (console + arquivo)")
    logger.info("")
    logger.info("HISTÃ“RICO DE REQUISIÃ‡Ã•ES (SUPABASE):")
    if SUPABASE_ENABLED:
        logger.info("  [OK] Supabase HABILITADO - HistÃ³rico disponÃ­vel")
        logger.info("  - Salvamento automÃ¡tico apÃ³s anÃ¡lise OCR")
        logger.info("  - Status atualizado apÃ³s salvar admissÃ£o")
        logger.info("  - Endpoints: /api/historico/listar, /api/historico/<cod>, /api/historico/buscar-cpf/<cpf>")
    else:
        logger.warning("  [AVISO] Supabase DESABILITADO - HistÃ³rico nÃ£o disponÃ­vel")
        logger.warning("  - Verifique as credenciais em backend/.env")
        logger.warning("  - Execute: pip install supabase")
    logger.info("=" * 80)
    logger.info("")
    logger.info("AGUARDANDO REQUISICOES...")
    logger.info("")
    
    # Iniciar servidor Flask
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )


