"""
API Backend para Sistema de Admissão
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

# Carregar variáveis de ambiente do arquivo .env na pasta backend
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ============================================
# IMPORTAR CLIENTE SUPABASE (HISTÓRICO)
# ============================================
try:
    from supabase_client import supabase_manager
    SUPABASE_ENABLED = supabase_manager.is_connected()
except ImportError as e:
    print(f"⚠️ Módulo supabase_client não encontrado: {e}")
    print("⚠️ Execute: pip install supabase")
    SUPABASE_ENABLED = False
    supabase_manager = None

# Configurar encoding UTF-8 para o console do Windows (evita erros com emojis)
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# ========================================
# CONFIGURAÇÃO DE LOGGING
# ========================================
# Criar diretório de logs se não existir
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

# Handler para arquivo (rotação automática)
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

# Configurações da API de CPF (Receita Federal)
CPF_API_BASE_URL = "https://ws.hubdodesenvolvedor.com.br/v2/cpf/"
CPF_API_TOKEN = os.getenv('CPF_API_TOKEN', '196634210WxQHcjsiMD355017104')

# ========================================
# CONFIGURAÇÕES DO BANCO DE DADOS MYSQL
# ========================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'SENHA@ROOT'),
    'database': os.getenv('DB_NAME', 'newdb'),
    'charset': 'utf8mb4'
}

def buscar_ids_banco(cod_requisicao):
    """
    Busca IdConvenio, IdFontePagadora e IdLocalOrigem direto do banco de dados MySQL

    Args:
        cod_requisicao: Código da requisição (ex: '0040000356004')

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
            logger.info(f"[DB] IDs encontrados no banco para {cod_requisicao}: IdConvenio={resultado.get('IdConvenio')}, IdFontePagadora={resultado.get('IdFontePagadora')}, IdLocalOrigem={resultado.get('IdLocalOrigem')}")
            return resultado
        else:
            logger.warning(f"[DB] Requisição {cod_requisicao} não encontrada no banco")
            return {'IdConvenio': None, 'IdFontePagadora': None, 'IdLocalOrigem': None}

    except Exception as e:
        logger.error(f"[DB] Erro ao buscar IDs do banco para {cod_requisicao}: {e}")
        return {'IdConvenio': None, 'IdFontePagadora': None, 'IdLocalOrigem': None}

def buscar_dados_paciente_via_api(cod_requisicao):
    """
    Busca dados do paciente através do requisicaoResultado da API
    
    Args:
        cod_requisicao: Código da requisição
        
    Returns:
        dict com dados do paciente da API ou None
    """
    try:
        logger.info(f"[API] Buscando dados do paciente via requisicaoResultado: {cod_requisicao}")
        
        dat_resultado = {"codRequisicao": cod_requisicao}
        resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

        if resposta_resultado.get("dat", {}).get("sucesso") == 1:
            dados_resultado = resposta_resultado.get("dat", {})
            paciente_api = dados_resultado.get("paciente", {})
            
            if paciente_api:
                logger.info(f"[API] ✅ Dados do paciente obtidos via API")
                
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
                }
                
                # Endereço pode vir como objeto
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
                logger.warning(f"[API] ⚠️ Paciente não encontrado no resultado da API")
                return None
        else:
            logger.warning(f"[API] ⚠️ Falha ao buscar via requisicaoResultado")
            return None

    except Exception as e:
        logger.error(f"[API] ❌ Erro ao buscar dados via API: {e}")
        return None


def buscar_dados_completos_paciente(cod_paciente):
    """
    Busca TODOS os dados do paciente direto do banco de dados (FALLBACK)

    Args:
        cod_paciente: Código do paciente

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
            logger.warning(f"[DB] Paciente {cod_paciente} não encontrado no banco")
            return None

    except Exception as e:
        logger.error(f"[DB] Erro ao buscar dados do paciente {cod_paciente}: {e}")
        return None

def buscar_requisicao_correspondente(cod_requisicao):
    """
    Busca requisição correspondente seguindo a regra:
    - Se começa com 0085 → busca correspondente 0200
    - Se começa com 0200 → busca correspondente 085

    Retorna dados do PACIENTE da requisição correspondente para sincronização

    Args:
        cod_requisicao: Código da requisição (ex: '0085075767003' ou '0200051495002')

    Returns:
        dict com dados do paciente da requisição correspondente ou None
    """
    try:
        # Verificar tipo de requisição
        if cod_requisicao.startswith('0085'):
            tipo_atual = '0085'
            tipo_correspondente = '0200'
            prefixo_busca = '0200%'
        elif cod_requisicao.startswith('0200'):
            tipo_atual = '0200'
            tipo_correspondente = '0085'
            prefixo_busca = '0085%'
        else:
            # Não é uma requisição que precisa de sincronização
            return None

        logger.info(f"[DB_SYNC] Requisicao {tipo_atual}: {cod_requisicao} -> Buscando correspondente {tipo_correspondente}...")

        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # ESTRATÉGIA: Buscar requisição correspondente do MESMO PACIENTE e MESMA DATA
        query = """
            SELECT
                r2.CodRequisicao,
                r2.IdConvenio,
                r2.IdFontePagadora,
                r2.IdLocalOrigem,
                r2.CodPaciente,
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
                t2.NumTelefone as TelFixo
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
            LIMIT 1
        """

        cursor.execute(query, (prefixo_busca, cod_requisicao))
        resultado = cursor.fetchone()

        cursor.close()
        connection.close()

        if resultado:
            logger.info(f"[DB_SYNC] ✅ Requisição correspondente encontrada: {resultado['CodRequisicao']}")
            logger.info(f"[DB_SYNC]    Paciente: {resultado.get('NomePaciente')} | CPF: {resultado.get('CPF')}")
            return resultado
        else:
            logger.info(f"[DB_SYNC] ⚠️ Nenhuma requisição correspondente encontrada para {cod_requisicao}")
            return None

    except Exception as e:
        logger.error(f"[DB_SYNC] Erro ao buscar requisição correspondente: {e}")
        return None

def buscar_requisicao_correspondente_aplis(cod_requisicao):
    """
    Busca requisição correspondente DIRETO DO APLIS (sem depender do banco local)

    Regra:
    - Se começa com 0085 → busca 0200 com mesmo sufixo
    - Se começa com 0200 → busca 0085 com mesmo sufixo

    Exemplo:
    - 0085075447003 → 0200075447003
    - 0200051653008 → 0085051653008

    Args:
        cod_requisicao: Código da requisição

    Returns:
        dict com dados do paciente da requisição correspondente ou None
    """
    try:
        # Verificar tipo de requisição
        if cod_requisicao.startswith('0085'):
            tipo_atual = '0085'
            tipo_correspondente = '0200'
            # Trocar prefixo: 0085075447003 → 0200075447003
            cod_correspondente = '0200' + cod_requisicao[4:]
        elif cod_requisicao.startswith('0200'):
            tipo_atual = '0200'
            tipo_correspondente = '0085'
            # Trocar prefixo: 0200051653008 → 0085051653008
            cod_correspondente = '0085' + cod_requisicao[4:]
        else:
            # Não é uma requisição que precisa de sincronização
            logger.info(f"[APLIS_SYNC] Requisição {cod_requisicao} não é tipo 0085 nem 0200")
            return None

        logger.info(f"[APLIS_SYNC] Requisição {tipo_atual}: {cod_requisicao}")
        logger.info(f"[APLIS_SYNC] Buscando correspondente {tipo_correspondente}: {cod_correspondente}")

        # Buscar no apLIS usando requisicaoListar com filtro por código
        # ESTRATÉGIA: Buscar nos últimos 365 dias
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
        logger.info(f"[APLIS_SYNC] Encontradas {len(lista)} requisições no período")

        # Procurar a requisição correspondente na lista
        for req in lista:
            if req.get("CodRequisicao") == cod_correspondente:
                logger.info(f"[APLIS_SYNC] ✅ Requisição correspondente encontrada: {cod_correspondente}")
                logger.info(f"[APLIS_SYNC]    Paciente: {req.get('NomPaciente')} | CPF: {req.get('CPF')}")

                # Retornar dados no mesmo formato da função do banco
                return {
                    "CodRequisicao": req.get("CodRequisicao"),
                    "CodPaciente": req.get("CodPaciente"),
                    "NomePaciente": req.get("NomPaciente"),
                    "CPF": req.get("CPF"),
                    "DtaNasc": req.get("DtaNascimento"),  # Pode vir em formatos diferentes
                    "Sexo": req.get("Sexo"),
                    # Outros campos do apLIS (podem não existir)
                    "IdConvenio": req.get("IdConvenio"),
                    "IdFontePagadora": req.get("IdFontePagadora"),
                    "IdLocalOrigem": req.get("IdLocalOrigem")
                }

        logger.warning(f"[APLIS_SYNC] ⚠️ Requisição correspondente {cod_correspondente} não encontrada no período")
        return None

    except Exception as e:
        logger.error(f"[APLIS_SYNC] Erro ao buscar correspondente no apLIS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# ========================================
# FUNÇÃO PARA CALCULAR DATA DE NASCIMENTO A PARTIR DA IDADE
# ========================================

def calcular_data_nascimento_por_idade(idade_formatada):
    """
    Calcula a data de nascimento a partir da idade formatada.

    Args:
        idade_formatada (str): Idade no formato "48 anos", "48 anos 10 meses" ou "48 anos 10 meses 10 dias"

    Returns:
        str: Data de nascimento no formato YYYY-MM-DD ou None se não conseguir calcular

    Exemplos:
        "48 anos" → "1977-01-26" (considerando hoje como 2026-01-26)
        "48 anos 10 meses" → "1977-03-26"
        "48 anos 10 meses 10 dias" → "1977-03-16"
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

        # Padrão: "48 anos 10 meses 10 dias" ou "48 anos" ou "48 anos 10 meses"
        match_anos = re.search(r'(\d+)\s*anos?', idade_formatada, re.IGNORECASE)
        match_meses = re.search(r'(\d+)\s*meses?', idade_formatada, re.IGNORECASE)
        match_dias = re.search(r'(\d+)\s*dias?', idade_formatada, re.IGNORECASE)

        if match_anos:
            anos = int(match_anos.group(1))
        if match_meses:
            meses = int(match_meses.group(1))
        if match_dias:
            dias = int(match_dias.group(1))

        # Se não encontrou nenhum valor, retornar None
        if anos == 0 and meses == 0 and dias == 0:
            return None

        # Calcular data de nascimento
        hoje = datetime.now()
        data_nascimento = hoje - relativedelta(years=anos, months=meses, days=dias)

        logger.info(f"[CALC_IDADE] '{idade_formatada}' → Data Nascimento: {data_nascimento.strftime('%Y-%m-%d')}")
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
        """Aguarda se necessário para respeitar rate limit"""
        current_time = time.time()

        # Remover requisições antigas (mais de 60 segundos)
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()

        # Se atingiu o limite de requisições por minuto, aguardar
        if len(self.request_times) >= self.max_rpm:
            oldest_request = self.request_times[0]
            wait_time = 60 - (current_time - oldest_request)
            if wait_time > 0:
                logger.warning(f"[RATE LIMIT] Atingido limite de {self.max_rpm} RPM. Aguardando {wait_time:.1f}s...")
                time.sleep(wait_time)
                current_time = time.time()

        # Garantir delay mínimo entre requisições
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            wait_time = self.min_delay - time_since_last
            logger.info(f"[RATE LIMIT] Aguardando {wait_time:.1f}s (delay mínimo entre requests)")
            time.sleep(wait_time)
            current_time = time.time()

        # Registrar esta requisição
        self.request_times.append(current_time)
        self.last_request_time = current_time
        logger.debug(f"[RATE LIMIT] Requisições no último minuto: {len(self.request_times)}/{self.max_rpm}")

# Instância global do rate limiter
# Configuração balanceada para evitar 429
vertex_rate_limiter = VertexAIRateLimiter(max_requests_per_minute=5, min_delay_seconds=10)

app = Flask(__name__)
# Configurar CORS para aceitar requisições de qualquer origem (necessário para ngrok)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Permite qualquer origem (ngrok, localhost, etc)
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ========================================
# REGISTRAR BLUEPRINTS
# ========================================
# Blueprint de autenticação customizada (antiga - compatibilidade)
try:
    from api_auth import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("[OK] Blueprint de autenticação legado registrado com sucesso!")
except ImportError as e:
    logger.warning(f"[AVISO] Não foi possível registrar blueprint de autenticação legado: {e}")

# Blueprint de autenticação Supabase (nova - compartilhada com outro sistema)
try:
    from api_auth_supabase import auth_supabase_bp
    app.register_blueprint(auth_supabase_bp)
    logger.info("[OK] Blueprint de autenticação Supabase registrado com sucesso!")
except ImportError as e:
    logger.warning(f"[AVISO] Não foi possível registrar blueprint de autenticação Supabase: {e}")

# ========================================
# MIDDLEWARE DE LOGGING
# ========================================
@app.before_request
def log_request_info():
    """Log de todas as requisições recebidas"""
    logger.info("=" * 80)
    logger.info(f" REQUISIÇÃO RECEBIDA")
    logger.info(f"   Método: {request.method}")
    logger.info(f"   URL: {request.url}")
    logger.info(f"   Path: {request.path}")
    logger.info(f"   Host: {request.host}")
    logger.info(f"   Remote Addr: {request.remote_addr}")
    logger.info(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    logger.info(f"   Origin: {request.headers.get('Origin', 'N/A')}")
    logger.info(f"   Referer: {request.headers.get('Referer', 'N/A')}")

    # Log do corpo da requisição (apenas para POST/PUT)
    if request.method in ['POST', 'PUT']:
        try:
            if request.is_json:
                logger.debug(f"   Body (JSON): {json.dumps(request.get_json(), indent=2, ensure_ascii=False)[:500]}")
            elif request.data:
                logger.debug(f"   Body (raw): {request.data[:500]}")
        except Exception as e:
            logger.warning(f"   Erro ao logar body: {e}")

    logger.info("=" * 80)

@app.after_request
def log_response_info(response):
    """Log de todas as respostas enviadas"""
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
    """Log de erros não tratados"""
    logger.error("=" * 80)
    logger.error(f" ERRO NÃO TRATADO")
    logger.error(f"   Tipo: {type(e).__name__}")
    logger.error(f"   Mensagem: {str(e)}")
    logger.error(f"   Request: {request.method} {request.url}")
    logger.exception("   Stack trace:")
    logger.error("=" * 80)

    return jsonify({
        "erro": f"{type(e).__name__}: {str(e)}",
        "detalhes": "Erro interno do servidor - verifique os logs"
    }), 500

# Diretório temporário para imagens
TEMP_IMAGES_DIR = os.path.join(tempfile.gettempdir(), 'admissao_images')
os.makedirs(TEMP_IMAGES_DIR, exist_ok=True)

# ========================================
# CACHE DE MÉDICOS, CONVÊNIOS E INSTITUIÇÕES (CSVs)
# ========================================
# Dicionários globais para busca rápida
MEDICOS_CACHE = {}  # {CRM_UF: {id, nome, crm, uf}}
CONVENIOS_CACHE = {}  # {IdConvenio: {id, nome}}
INSTITUICOES_CACHE = {}  # {IdInstituicao: {id, nome}}

def carregar_medicos_csv():
    """Carrega médicos do CSV para cache em memória"""
    global MEDICOS_CACHE
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'dados', 'medicos_extraidos_20260120_155027.csv')

    if not os.path.exists(csv_path):
        logger.warning(f"[CSV] Arquivo de médicos não encontrado: {csv_path}")
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
        logger.info(f"[CSV] OK - {len(MEDICOS_CACHE)} médicos carregados do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar médicos: {e}")

def carregar_convenios_csv():
    """Carrega convênios do CSV para cache em memória"""
    global CONVENIOS_CACHE
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'dados', 'convenios_extraidos_20260120_155027.csv')

    if not os.path.exists(csv_path):
        logger.warning(f"[CSV] Arquivo de convênios não encontrado: {csv_path}")
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
        logger.info(f"[CSV] OK - {len(CONVENIOS_CACHE)} convênios carregados do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar convênios: {e}")

def carregar_instituicoes_csv():
    """Carrega instituições do CSV para cache em memória"""
    global INSTITUICOES_CACHE
    
    # Buscar o arquivo CSV mais recente de instituições
    pasta_dados = os.path.join(os.path.dirname(__file__), '..', 'dados')
    arquivos_instituicoes = []
    
    if os.path.exists(pasta_dados):
        for arquivo in os.listdir(pasta_dados):
            if arquivo.startswith('instituicoes_extraidas_') and arquivo.endswith('.csv'):
                caminho_completo = os.path.join(pasta_dados, arquivo)
                arquivos_instituicoes.append(caminho_completo)
    
    if not arquivos_instituicoes:
        logger.warning(f"[CSV] Nenhum arquivo de instituições encontrado em {pasta_dados}")
        logger.warning(f"[CSV] Execute: python backend/extrair_instituicoes.py")
        return
    
    # Usar o arquivo mais recente (ordenar por nome, que tem timestamp)
    csv_path = sorted(arquivos_instituicoes)[-1]
    logger.info(f"[CSV] Carregando instituições de: {os.path.basename(csv_path)}")

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_instituicao = row['IdInstituicao']
                INSTITUICOES_CACHE[id_instituicao] = {
                    'id': id_instituicao,
                    'nome': row['NomFantasia']
                }
        logger.info(f"[CSV] OK - {len(INSTITUICOES_CACHE)} instituições carregadas do CSV")
    except Exception as e:
        logger.error(f"[CSV] Erro ao carregar instituições: {e}")

def buscar_medico_por_crm(crm, uf):
    """Busca médico no cache por CRM e UF"""
    chave = f"{crm}_{uf}"
    return MEDICOS_CACHE.get(chave)

def buscar_convenio_por_id(id_convenio):
    """Busca convênio no cache por ID"""
    return CONVENIOS_CACHE.get(str(id_convenio))

def buscar_instituicao_por_id(id_instituicao):
    """Busca instituição no cache por ID"""
    return INSTITUICOES_CACHE.get(str(id_instituicao))

def buscar_instituicao_por_nome(nome_busca):
    """
    Busca instituição no cache por nome (busca parcial, case-insensitive)
    
    Estratégia de busca:
    1. Busca exata
    2. Busca por palavra-chave (primeira palavra significativa)
    3. Busca parcial
    
    Args:
        nome_busca (str): Nome ou parte do nome da instituição
        
    Returns:
        dict: Dados da instituição {'id': int, 'nome': str} ou None se não encontrar
    """
    if not nome_busca or not isinstance(nome_busca, str):
        return None
        
    nome_busca_upper = nome_busca.upper().strip()
    logger.info(f"[BuscarInstituicao] 🔍 Procurando instituição: '{nome_busca}'")
    logger.debug(f"[BuscarInstituicao] Total no cache: {len(INSTITUICOES_CACHE)}")
    
    # 1. Busca exata primeiro
    for id_inst, inst_data in INSTITUICOES_CACHE.items():
        nome_cache = inst_data.get('nome', '').upper()
        if nome_cache == nome_busca_upper:
            logger.info(f"[BuscarInstituicao] ✅ Encontrada (exata): ID={id_inst}, Nome={inst_data.get('nome')}")
            return inst_data
    
    # 2. Busca por palavra-chave (ex: "CASSI - Caixa..." → "CASSI")
    # Pegar primeira palavra significativa (>= 3 caracteres)
    palavras = nome_busca_upper.split()
    palavra_chave = None
    for palavra in palavras:
        palavra_limpa = palavra.strip(',-()[]')
        if len(palavra_limpa) >= 3 and palavra_limpa not in ['DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'EM']:
            palavra_chave = palavra_limpa
            break
    
    if palavra_chave:
        logger.debug(f"[BuscarInstituicao] Palavra-chave extraída: '{palavra_chave}'")
        for id_inst, inst_data in INSTITUICOES_CACHE.items():
            nome_cache = inst_data.get('nome', '').upper()
            # Busca a palavra no início do nome
            if nome_cache.startswith(palavra_chave):
                logger.info(f"[BuscarInstituicao] ✅ Encontrada (palavra-chave): ID={id_inst}, Nome={inst_data.get('nome')}")
                return inst_data
    
    # 3. Busca parcial (contém)
    for id_inst, inst_data in INSTITUICOES_CACHE.items():
        nome_cache = inst_data.get('nome', '').upper()
        if nome_busca_upper in nome_cache or nome_cache in nome_busca_upper:
            logger.info(f"[BuscarInstituicao] ✅ Encontrada (parcial): ID={id_inst}, Nome={inst_data.get('nome')}")
            return inst_data
    
    logger.warning(f"[BuscarInstituicao] ⚠️ Instituição '{nome_busca}' não encontrada no cache")
    logger.debug(f"[BuscarInstituicao] Amostra do cache: {list(INSTITUICOES_CACHE.values())[:5]}")
    return None

def obter_id_convenio_default():
    """
    Busca um ID de convênio válido para usar como default
    Prioridade: 1) PARTICULAR, 2) Primeiro do cache

    Returns:
        int: ID do convênio default ou None se cache vazio
    """
    if not CONVENIOS_CACHE:
        logger.warning("[Default] Cache de convênios vazio!")
        return None

    # Tentar encontrar "PARTICULAR" ou similar
    for id_convenio, convenio_data in CONVENIOS_CACHE.items():
        nome = convenio_data.get('nome', '').upper()
        if 'PARTICULAR' in nome or 'PRIVADO' in nome or 'SEM CONVENIO' in nome:
            logger.info(f"[Default] ✅ Convênio default encontrado: ID={id_convenio}, Nome={convenio_data.get('nome')}")
            return int(id_convenio)

    # Se não encontrou PARTICULAR, pegar o primeiro disponível
    primeiro_id = list(CONVENIOS_CACHE.keys())[0]
    primeiro_nome = CONVENIOS_CACHE[primeiro_id].get('nome')
    logger.info(f"[Default] ✅ Usando primeiro convênio: ID={primeiro_id}, Nome={primeiro_nome}")
    return int(primeiro_id)

def obter_id_instituicao_default():
    """
    Busca um ID de instituição válido para usar como default

    Returns:
        int: ID da instituição default ou None se cache vazio
    """
    if not INSTITUICOES_CACHE:
        logger.warning("[Default] Cache de instituições vazio!")
        return None

    # Pegar a primeira disponível
    primeiro_id = list(INSTITUICOES_CACHE.keys())[0]
    primeiro_nome = INSTITUICOES_CACHE[primeiro_id].get('nome')
    logger.info(f"[Default] ✅ Instituição default: ID={primeiro_id}, Nome={primeiro_nome}")
    return int(primeiro_id)

def buscar_instituicao_por_nome(nome_busca):
    """
    Busca instituição (fonte pagadora) por nome (busca parcial, case-insensitive)
    
    Args:
        nome_busca (str): Nome ou parte do nome da instituição
    
    Returns:
        dict: {'id': int, 'nome': str} ou None se não encontrar
    """
    if not nome_busca or not INSTITUICOES_CACHE:
        return None
    
    nome_busca_upper = nome_busca.upper().strip()
    
    # Busca exata primeiro
    for id_inst, dados_inst in INSTITUICOES_CACHE.items():
        if dados_inst.get('nome', '').upper() == nome_busca_upper:
            logger.info(f"[BuscarInstituicao] ✅ Match exato: ID={id_inst}, Nome={dados_inst.get('nome')}")
            return {'id': int(id_inst), 'nome': dados_inst.get('nome')}
    
    # Busca parcial (contém)
    for id_inst, dados_inst in INSTITUICOES_CACHE.items():
        nome_inst = dados_inst.get('nome', '').upper()
        if nome_busca_upper in nome_inst:
            logger.info(f"[BuscarInstituicao] ✅ Match parcial: ID={id_inst}, Nome={dados_inst.get('nome')}")
            return {'id': int(id_inst), 'nome': dados_inst.get('nome')}
    
    logger.warning(f"[BuscarInstituicao] ⚠️ Instituição '{nome_busca}' não encontrada no cache")
    return None

def obter_id_medico_default():
    """
    Busca um ID de médico válido para usar como default

    Returns:
        int: ID do médico default ou None se cache vazio
    """
    if not MEDICOS_CACHE:
        logger.warning("[Default] Cache de médicos vazio!")
        return None

    # Pegar o primeiro disponível
    primeiro_medico = list(MEDICOS_CACHE.values())[0]
    primeiro_id = primeiro_medico.get('id')
    primeiro_nome = primeiro_medico.get('nome')
    logger.info(f"[Default] ✅ Médico default: ID={primeiro_id}, Nome={primeiro_nome}")
    return int(primeiro_id)

def _buscar_convenio_nome(id_convenio):
    """Helper: Busca nome do convênio nos CSVs usando o ID"""
    logger.info(f"[Helper] 🔍 _buscar_convenio_nome chamado com ID: {id_convenio} (tipo: {type(id_convenio).__name__})")
    if not id_convenio:
        logger.info(f"[Helper] ⚠️ ID está vazio/None")
        return None
    try:
        logger.debug(f"[Helper] Total de convenios em cache: {len(CONVENIOS_CACHE)}")
        logger.debug(f"[Helper] Primeiras 5 chaves do cache: {list(CONVENIOS_CACHE.keys())[:5]}")

        convenio = buscar_convenio_por_id(id_convenio)
        if convenio:
            nome = convenio.get('nome')
            logger.info(f"[Helper] ✅ Convênio ID {id_convenio} ENCONTRADO: {nome}")
            return nome
        else:
            # Tentar buscar com conversão de tipo (int → str ou str → int)
            id_alt = int(id_convenio) if isinstance(id_convenio, str) else str(id_convenio)
            convenio_alt = CONVENIOS_CACHE.get(str(id_alt))
            if convenio_alt:
                nome = convenio_alt.get('nome')
                logger.info(f"[Helper] ✅ Convênio ID {id_convenio} ENCONTRADO (conversão tipo): {nome}")
                return nome

            logger.warning(f"[Helper] ❌ Convênio ID {id_convenio} NÃO encontrado no cache")
            logger.debug(f"[Helper] IDs disponíveis (amostra): {list(CONVENIOS_CACHE.keys())[:10]}")
    except Exception as e:
        logger.error(f"[Helper] 💥 Erro: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Retornar None em vez de string fallback
    logger.info(f"[Helper] 📤 Retornando None (não encontrado)")
    return None

def _buscar_instituicao_nome(id_instituicao):
    """Helper: Busca nome da instituição nos CSVs usando o ID"""
    logger.info(f"[Helper] 🔍 _buscar_instituicao_nome chamado com ID: {id_instituicao} (tipo: {type(id_instituicao).__name__})")
    if not id_instituicao:
        logger.info(f"[Helper] ⚠️ ID está vazio/None")
        return None
    try:
        logger.debug(f"[Helper] Total de instituições em cache: {len(INSTITUICOES_CACHE)}")
        logger.debug(f"[Helper] Primeiras 5 chaves do cache: {list(INSTITUICOES_CACHE.keys())[:5]}")

        instituicao = buscar_instituicao_por_id(id_instituicao)
        if instituicao:
            nome = instituicao.get('nome')
            logger.info(f"[Helper] ✅ Instituição ID {id_instituicao} ENCONTRADA: {nome}")
            return nome
        else:
            # Tentar buscar com conversão de tipo (int → str ou str → int)
            id_alt = int(id_instituicao) if isinstance(id_instituicao, str) else str(id_instituicao)
            instituicao_alt = INSTITUICOES_CACHE.get(str(id_alt))
            if instituicao_alt:
                nome = instituicao_alt.get('nome')
                logger.info(f"[Helper] ✅ Instituição ID {id_instituicao} ENCONTRADA (conversão tipo): {nome}")
                return nome

            logger.warning(f"[Helper] ❌ Instituição ID {id_instituicao} NÃO encontrada no cache")
            logger.debug(f"[Helper] IDs disponíveis (amostra): {list(INSTITUICOES_CACHE.keys())[:10]}")
    except Exception as e:
        logger.error(f"[Helper] 💥 Erro: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Retornar None em vez de string fallback
    logger.info(f"[Helper] 📤 Retornando None (não encontrado)")
    return None

# Carregar CSVs na inicialização
logger.info("[INIT] Carregando dados dos CSVs...")
carregar_medicos_csv()
carregar_convenios_csv()
carregar_instituicoes_csv()

# Configurações apLIS - USAR VARIÁVEIS DE AMBIENTE
APLIS_URL = os.getenv('APLIS_BASE_URL', 'https://lab.aplis.inf.br/api/integracao.php')
APLIS_USERNAME = os.getenv('APLIS_USUARIO', 'api.lab')
APLIS_PASSWORD = os.getenv('APLIS_SENHA', '')  # ⚠️ CONFIGURE NO .env
APLIS_HEADERS = {"Content-Type": "application/json"}

# Configurações AWS S3
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


def fazer_requisicao_aplis(cmd, dat):
    """
    Função genérica para fazer requisições ao apLIS usando a metodologia requisicaoListar

    Args:
        cmd (str): Comando a executar (ex: "requisicaoListar", "admissaoSalvar")
        dat (dict): Dados a enviar no campo "dat"

    Returns:
        dict: Resposta da API apLIS
    """
    payload = {
        "ver": 1,
        "cmd": cmd,
        "dat": dat
    }

    data = json.dumps(payload)
    logger.info(f"[apLIS] Enviando requisição: {cmd}")
    logger.info(f"[apLIS] Payload completo: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(
            APLIS_URL,
            auth=(APLIS_USERNAME, APLIS_PASSWORD),
            headers=APLIS_HEADERS,
            data=data
        )

        logger.info(f"[apLIS] Status Code: {response.status_code}")

        try:
            resposta_json = response.json()
            logger.info(f"[apLIS] Resposta JSON completa: {json.dumps(resposta_json, indent=2, ensure_ascii=False)}")

            if resposta_json.get("dat") and resposta_json["dat"].get("sucesso") == 1:
                logger.info(f"[apLIS] Requisição bem-sucedida para comando: {cmd}")
                return resposta_json
            else:
                logger.warning(f"[apLIS] Resposta com sucesso != 1: {resposta_json}")
                return resposta_json

        except ValueError:
            logger.error(f"[apLIS] Resposta não está em JSON: {response.text}")
            return {"erro": "Resposta inválida do apLIS", "texto": response.text, "sucesso": 0, "dat": {}}

    except requests.exceptions.RequestException as e:
        logger.error(f"[apLIS] Erro na requisição: {str(e)}")
        return {"erro": f"Erro na requisição: {str(e)}", "sucesso": 0, "dat": {}}
    except Exception as e:
        logger.error(f"[apLIS] Erro inesperado: {str(e)}")
        return {"erro": f"Erro inesperado: {str(e)}", "sucesso": 0, "dat": {}}


def consultar_cpf_receita_federal(cpf, data_nascimento):
    """
    Consulta CPF na API da Receita Federal (HubDoDesenvolvedor)

    Args:
        cpf (str): CPF no formato XXX.XXX.XXX-XX ou apenas números
        data_nascimento (str): Data de nascimento no formato DD/MM/YYYY ou YYYY-MM-DD

    Returns:
        dict: Dados validados da Receita Federal ou None se houver erro
    """
    try:
        # Remove formatação do CPF (pontos e traços)
        cpf_limpo = cpf.replace(".", "").replace("-", "").replace("/", "").strip() if cpf else ""

        if not cpf_limpo or len(cpf_limpo) != 11:
            logger.warning(f"[CPF_API] CPF invalido ou vazio: {cpf}")
            return None

        # IMPORTANTE: A API funciona melhor SEM a data de nascimento (enviar vazia)
        # Se enviar data, a API pode rejeitar com "Parametro Invalido"
        data_param = ""

        # Monta a URL com os parâmetros (data sempre vazia)
        url = f"{CPF_API_BASE_URL}?cpf={cpf_limpo}&data={data_param}&token={CPF_API_TOKEN}"

        logger.info(f"[CPF_API] Consultando CPF: {cpf_limpo}")
        
        # Headers para evitar bloqueio de bot (User-Agent)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        # Faz a requisição com Retry (3 tentativas)
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
            logger.error(f"[CPF_API] Falha total na conexão. Último erro: {last_error}")
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

            # Formatar data de nascimento para DD/MM/YYYY (garantir formato numérico)
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
    Valida dados do CPF com a Receita Federal e corrige se necessário.
    Prioriza dados da Receita Federal sobre dados do apLIS.

    Args:
        dados_aplis (dict): Dados vindos do apLIS
        dados_sistema_antigo (dict): Dados do sistema antigo (opcional)

    Returns:
        dict: Dados corrigidos/validados com informações da Receita Federal
    """
    try:
        cpf = dados_aplis.get("CPF")
        data_nascimento = None

        # Tentar obter data de nascimento do sistema antigo primeiro
        if dados_sistema_antigo and dados_sistema_antigo.get("dtaNasc"):
            data_nascimento = dados_sistema_antigo.get("dtaNasc")

        # Se não tem CPF, não há o que validar
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
        logger.info(f"[ValidarCPF] Iniciando validação de CPF: {cpf}")
        dados_receita = consultar_cpf_receita_federal(cpf, data_nascimento)

        if not dados_receita:
            logger.warning("[ValidarCPF] Não foi possível validar CPF na Receita Federal")
            return {
                "dados_corrigidos": False,
                "fonte_dados": "aplis",
                "aviso": "Não foi possível validar CPF na Receita Federal",
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

        # Verificar se há divergências
        divergencias = []
        dados_corrigidos = False

        # Comparar nomes (ignora maiúsculas/minúsculas e espaços extras)
        if nome_aplis and nome_receita and nome_aplis != nome_receita:
            divergencias.append(f"Nome: apLIS='{dados_aplis.get('NomPaciente')}' → Receita='{dados_receita.get('nome')}'")
            dados_corrigidos = True

        # Comparar CPFs
        cpf_aplis_limpo = cpf.replace(".", "").replace("-", "")
        if cpf_aplis_limpo != cpf_receita:
            divergencias.append(f"CPF: apLIS='{cpf}' → Receita='{dados_receita.get('cpf')}'")
            dados_corrigidos = True

        # Comparar data de nascimento
        if data_nascimento and data_nasc_receita:
            # Normalizar formatos para comparação
            data_aplis_norm = data_nascimento.replace("/", "").replace("-", "")
            data_receita_norm = data_nasc_receita.replace("/", "").replace("-", "")

            if data_aplis_norm != data_receita_norm:
                divergencias.append(f"Data Nasc: Sistema='{data_nascimento}' → Receita='{data_nasc_receita}'")
                dados_corrigidos = True

        # Log das divergências
        if divergencias:
            logger.warning(f"[ValidarCPF] ⚠️ DIVERGÊNCIAS ENCONTRADAS:")
            for div in divergencias:
                logger.warning(f"[ValidarCPF]   - {div}")
            logger.info(f"[ValidarCPF] ✅ Dados serão corrigidos com informações da Receita Federal")
        else:
            logger.info(f"[ValidarCPF] ✅ Dados conferem com a Receita Federal")

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
            # Dados comparativos para exibição
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
        logger.error(f"[ValidarCPF] ❌ Erro ao validar CPF: {e}")
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


def salvar_admissao_aplis(dados_admissao):
    """
    Salva uma admissão/requisição no apLIS usando a nova metodologia genérica
    """
    logger.info(f"[Admissão] Salvando admissão com dados: {len(str(dados_admissao))} bytes")
    return fazer_requisicao_aplis("admissaoSalvar", dados_admissao)


def buscar_dados_paciente_sistema_antigo(cod_paciente=None, cpf=None):
    """
    Busca dados COMPLETOS do paciente buscando requisições ANTIGAS do mesmo paciente

    ESTRATÉGIA: Como o `requisicaoListar` do sistema novo não retorna dados completos
    do paciente (dtaNasc, RG, endereço), buscamos requisições antigas (com 1+ dia de atraso)
    para obter esses dados complementares que podem ter sido salvos anteriormente.

    Dados que buscamos:
    - Data de nascimento
    - RG
    - Sexo
    - Telefone
    - Endereço completo

    Args:
        cod_paciente (str): Código do paciente
        cpf (str): CPF do paciente

    Returns:
        dict: Dados completos do paciente ou None se não encontrar
    """
    try:
        logger.info(f"[SistemaComplementar] Buscando dados históricos do paciente: codPaciente={cod_paciente}, cpf={cpf}")

        # IMPORTANTE: Como requisicaoListar do sistema NOVO não retorna dados completos
        # do paciente, vamos buscar usando requisicaoResultado ou fazer busca ampla
        # em requisições antigas do paciente

        if not cod_paciente:
            logger.warning(f"[SistemaComplementar] Código do paciente não fornecido, impossível buscar dados")
            return None

        # Buscar requisições antigas do paciente (últimos 2 anos)
        hoje = datetime.now()
        periodo_fim = (hoje - timedelta(days=1)).strftime("%Y-%m-%d")  # Ontem (dados com atraso)
        periodo_ini = (hoje - timedelta(days=730)).strftime("%Y-%m-%d")  # 2 anos atrás

        dat = {
            "tipoData": 1,  # Data de solicitação
            "periodoIni": periodo_ini,
            "periodoFim": periodo_fim,
            "idPaciente": int(cod_paciente),
            "ordenar": "DtaSolicitacao",
            "pagina": 1,
            "tamanho": 1  # Apenas a mais recente
        }

        logger.debug(f"[SistemaComplementar] Buscando requisições antigas: {dat}")

        # Fazer requisição usando requisicaoListar (modo usuários internos)
        resposta = fazer_requisicao_aplis("requisicaoListar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            lista_requisicoes = resposta.get("dat", {}).get("lista", [])

            if lista_requisicoes and len(lista_requisicoes) > 0:
                # Pegar a requisição mais recente
                req_antiga = lista_requisicoes[0]
                cod_req_antiga = req_antiga.get("CodRequisicao")

                logger.info(f"[SistemaComplementar] ✅ Encontrada requisição antiga: {cod_req_antiga}")

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

                    logger.info(f"[SistemaComplementar] ✅ Dados completos obtidos via requisicaoResultado!")
                    logger.debug(f"[SistemaComplementar] Dados paciente RAW: {json.dumps(paciente_completo, indent=2, ensure_ascii=False)[:1000]}")

                    # Verificar todos os campos disponíveis no paciente_completo
                    logger.info(f"[SistemaComplementar] 🔍 Campos disponíveis em paciente_completo: {list(paciente_completo.keys())}")

                    # Extrair dados do paciente
                    # Tentar pegar RG, telefone e endereço se existirem
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

                    logger.info(f"[SistemaComplementar] Campos extraídos: dtaNasc={dados_paciente.get('dtaNasc')}, "
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
                logger.info(f"[SistemaComplementar] Nenhuma requisição antiga encontrada para o paciente")
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
    Lista requisições do apLIS usando requisicaoListar
    
    Args:
        id_evento (str): ID do evento
        periodo_ini (str): Data inicial (YYYY-MM-DD)
        periodo_fim (str): Data final (YYYY-MM-DD)
        ordenar (str): Campo para ordenação (padrão: IdRequisicao)
        paginaAtual (int): Número da página a buscar (padrão: 1)
    
    Returns:
        dict: Resposta com requisições
    """
    dat = {
        "ordenar": ordenar,
        "idEvento": str(id_evento),
        "periodoIni": periodo_ini,
        "periodoFim": periodo_fim,
        "paginaAtual": paginaAtual  # ← Parâmetro de paginação
    }
    
    logger.info(f"[Listagem] Listando requisições do evento {id_evento} de {periodo_ini} a {periodo_fim} (página {paginaAtual})")
    return fazer_requisicao_aplis("requisicaoListar", dat)


def listar_requisicoes_detalhadas(id_evento, periodo_ini, periodo_fim, enriquecer=True):
    """
    Lista requisições do apLIS com dados PRIMÁRIOS + complementares enriquecidos
    
    ⭐ AGORA BUSCA TODAS AS PÁGINAS - Não fica limitado aos primeiros 50 registros!
    
    Esta função integra as duas metodologias:
    1. PRIMÁRIA (requisicaoListar): Traz dados básicos e importantes
       - Código da requisição
       - CPF do paciente
       - Nome do paciente
       - Data da coleta
       - ID do médico
       
    2. COMPLEMENTAR (enriquecimento): Adiciona informações complementares
       - Dados do médico completos
       - Convenio
       - Fonte pagadora
       - Local de origem
       - Dados clínicos
    
    Args:
        id_evento (str): ID do evento
        periodo_ini (str): Data inicial (YYYY-MM-DD)
        periodo_fim (str): Data final (YYYY-MM-DD)
        enriquecer (bool): Se deve buscar dados complementares (padrão: True)
    
    Returns:
        dict: Lista de requisições com dados primários e complementares (TODAS as páginas)
    """
    try:
        logger.info(f"[ListagemDetalhada] Iniciando busca: evento={id_evento}, período={periodo_ini} a {periodo_fim}")
        
        # PASSO 1: Obter TODAS as páginas de requisições
        lista_requisicoes_total = []
        pagina_atual = 1
        
        while True:
            logger.info(f"[ListagemDetalhada] Buscando página {pagina_atual}...")
            
            # Fazer requisição COM parâmetro de página
            resposta = listar_requisicoes_aplis(id_evento, periodo_ini, periodo_fim, "CodRequisicao", paginaAtual=pagina_atual)
            
            if resposta.get("dat", {}).get("sucesso") != 1:
                if pagina_atual == 1:
                    # Erro na primeira página - problema real
                    logger.warning(f"[ListagemDetalhada] Falha ao obter lista primária: {resposta}")
                    return resposta
                else:
                    # Erro em página posterior - parar a paginação
                    logger.info(f"[ListagemDetalhada] Finalizando paginação (erro na página {pagina_atual})")
                    break
            
            dados_resposta = resposta.get("dat", {})
            lista_pagina = dados_resposta.get("lista", [])
            
            if not lista_pagina:
                logger.info(f"[ListagemDetalhada] Página {pagina_atual} vazia - finalizando paginação")
                break
            
            logger.info(f"[ListagemDetalhada] Página {pagina_atual}: {len(lista_pagina)} requisições")
            lista_requisicoes_total.extend(lista_pagina)
            
            # Verificar se há mais páginas
            qtd_paginas = dados_resposta.get("qtdPaginas", 1)
            registros_totais = dados_resposta.get("registros", len(lista_requisicoes_total))
            logger.debug(f"[ListagemDetalhada] Total de páginas: {qtd_paginas}, registros: {registros_totais}, página atual: {pagina_atual}")
            
            if pagina_atual >= qtd_paginas:
                logger.info(f"[ListagemDetalhada] Todas as {qtd_paginas} páginas foram obtidas ({registros_totais} registros)")
                break
            
            pagina_atual += 1
        
        logger.info(f"[ListagemDetalhada] ✅ TOTAL de requisições coletadas: {len(lista_requisicoes_total)}")
        
        if not enriquecer or len(lista_requisicoes_total) == 0:
            logger.info(f"[ListagemDetalhada] Retornando dados básicos (sem enriquecimento)")
            return {
                "dat": {
                    "sucesso": 1,
                    "lista": lista_requisicoes_total,
                    "total": len(lista_requisicoes_total),
                    "modo": "basico"
                }
            }
        
        # PASSO 2: Enriquecer dados complementares para cada requisição
        logger.info(f"[ListagemDetalhada] Iniciando enriquecimento de dados para {len(lista_requisicoes_total)} requisições")
        
        requisicoes_enriquecidas = []
        
        for idx, req in enumerate(lista_requisicoes_total, 1):
            try:
                cod_requisicao = req.get("CodRequisicao")
                logger.debug(f"[ListagemDetalhada] [{idx}/{len(lista_requisicoes_total)}] Enriquecendo: {cod_requisicao}")

                # 🆕 TENTAR BUSCAR DADOS COMPLEMENTARES DO requisicaoResultado
                dados_resultado = None
                try:
                    dat_resultado = {"codRequisicao": cod_requisicao}
                    resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

                    if resposta_resultado.get("dat", {}).get("sucesso") == 1:
                        dados_resultado = resposta_resultado.get("dat", {})
                        logger.debug(f"[ListagemDetalhada] ✅ Dados complementares obtidos para {cod_requisicao}")
                except Exception as e:
                    logger.debug(f"[ListagemDetalhada] requisicaoResultado não disponível para {cod_requisicao}: {str(e)}")

                # Extrair nomes do requisicaoResultado (se disponível)
                nome_convenio = None
                nome_local_origem = None

                if dados_resultado:
                    # Convênio do resultado
                    if dados_resultado.get("paciente", {}).get("convenio"):
                        nome_convenio = dados_resultado["paciente"]["convenio"]

                    # Local de origem do resultado
                    if dados_resultado.get("localOrigem", {}).get("nome"):
                        nome_local_origem = dados_resultado["localOrigem"]["nome"]

                # Fallback para CSV se não veio do resultado
                if not nome_convenio and req.get("IdConvenio"):
                    nome_convenio = _buscar_convenio_nome(req.get("IdConvenio"))

                if not nome_local_origem and req.get("IdLocalOrigem"):
                    nome_local_origem = _buscar_instituicao_nome(req.get("IdLocalOrigem"))

                # Dados primários (já vieram do requisicaoListar)
                req_enriquecida = {
                    # ===== DADOS PRIMÁRIOS (da busca inicial) =====
                    "dados_primarios": {
                        "codRequisicao": req.get("CodRequisicao"),
                        "idRequisicao": req.get("IdRequisicao"),
                        "dtaColeta": req.get("DtaColeta") or req.get("DtaPrevista"),
                        "numGuia": req.get("NumGuiaConvenio") or req.get("NumExterno"),
                        "dadosClinicos": req.get("IndicacaoClinica") or req.get("NomExame")
                    },
                    # ===== DADOS DO PACIENTE (primários) =====
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
                        "id": req.get("IdConvenio"),  # ✅ ID do convênio
                        "nome": nome_convenio
                    },
                    "fontePagadora": {
                        "id": req.get("IdFontePagadora"),  # ✅ ID da fonte pagadora
                        "nome": None  # Não disponível na API apLIS
                    },
                    "localOrigem": {
                        "id": req.get("IdLocalOrigem"),  # ✅ ID do local de origem
                        "nome": nome_local_origem
                    },
                    # Metadata
                    "origem": "requisicaoListar + requisicaoResultado",
                    "enriquecido": True
                }
                
                requisicoes_enriquecidas.append(req_enriquecida)
                
            except Exception as e:
                logger.error(f"[ListagemDetalhada] Erro ao enriquecer requisição {cod_requisicao}: {str(e)}")
                # Ainda assim adiciona com dados básicos
                requisicoes_enriquecidas.append({
                    "codRequisicao": req.get("CodRequisicao"),
                    "paciente": {"nome": req.get("NomPaciente"), "cpf": req.get("CPF")},
                    "erro_enriquecimento": str(e)
                })
        
        logger.info(f"[ListagemDetalhada] ✅ Enriquecimento concluído: {len(requisicoes_enriquecidas)} requisições")
        
        # Retornar resposta com dados enriquecidos
        return {
            "dat": {
                "sucesso": 1,
                "lista": requisicoes_enriquecidas,
                "total": len(requisicoes_enriquecidas),
                "modo": "detalhado_enriquecido",
                "avisos": [
                    "Dados do paciente (dtaNasc, sexo, rg, endereço) vêm do OCR ou devem ser preenchidos manualmente",
                    "Dados primários garantidos: codRequisicao, CPF, nome do paciente, data da coleta",
                    f"Total de {len(requisicoes_enriquecidas)} requisições foram consultadas (TODAS as páginas)"
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
    Lista requisições do apLIS com dados PRIMÁRIOS e COMPLEMENTARES
    
    Esta função integra duas metodologias:
    1. PRIMÁRIA: Dados básicos e importantes (requisição, CPF, paciente)
    2. COMPLEMENTAR: Informações adicionais (médico, convênio, local origem, etc)
    
    Exemplo de requisição:
    {
        "idEvento": "50",
        "periodoIni": "2026-01-15",
        "periodoFim": "2026-01-15",
        "enriquecer": true  # (opcional, padrão: true) - Se deve buscar dados complementares
    }
    
    Resposta:
    {
        "sucesso": 1,
        "dados": {
            "lista": [
                {
                    "dados_primarios": { ... },      // Dados críticos: cod requisição, CPF, etc
                    "paciente": { ... },               // Nome, CPF (vem do requisicaoListar)
                    "medico": { ... },                 // CRM, UF
                    "dados_complementares": { ... },  // IDs de convênio, fonte pagadora, etc
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
        enriquecer = dados.get('enriquecer', True)  # Padrão: ativo
        
        if not all([id_evento, periodo_ini, periodo_fim]):
            return jsonify({
                "sucesso": 0,
                "erro": "Campos obrigatórios: idEvento, periodoIni, periodoFim"
            }), 400
        
        logger.info(f"[ListagemEndpoint] Requisição com enriquecimento={'ativo' if enriquecer else 'inativo'}")
        
        # Usar função integrada que combina primário + complementar
        resposta = listar_requisicoes_detalhadas(id_evento, periodo_ini, periodo_fim, enriquecer)
        
        return jsonify({
            "sucesso": 1 if resposta.get("dat", {}).get("sucesso") == 1 else 0,
            "dados": resposta.get("dat", {}),
            "mensagem": "Listagem obtida com sucesso (dados primários + complementares)" if resposta.get("dat", {}).get("sucesso") == 1 else "Erro ao listar"
        }), 200
        
    except Exception as e:
        logger.error(f"[ListagemEndpoint] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao listar requisições: {str(e)}"
        }), 500


@app.route('/api/requisicao/<cod_requisicao>', methods=['GET'])
def buscar_requisicao(cod_requisicao):
    """
    ✅ INTEGRALIZADO: Busca dados COMPLETOS de uma requisição
    
    AGORA INTEGRA:
    1. DADOS PRIMÁRIOS: Código requisição, CPF, nome paciente (via requisicaoListar)
    2. DADOS COMPLEMENTARES: Médico, convênio, fonte pagadora, local origem (via enriquecimento)
    3. IMAGENS: Do S3 (AWS)
    4. DADOS OCR: Vazios até processamento (preenchidos depois)
    
    Retorna estrutura única com todos os dados necessários para o frontend.
    """
    try:
        logger.info(f"[BuscarIntegrado] Iniciando busca para requisição: {cod_requisicao}")

        # ✅ NOVA ESTRATÉGIA: Busca DIRETA por código (SEM período específico)
        # Isso permite encontrar requisições mesmo em períodos antigos
        logger.info(f"[BuscarIntegrado] Tentando busca direta por código...")
        
        # PASSO 1: Busca direta usando código como filtro (SEM período)
        dat_direto = {
            "idEvento": "50",
            "codRequisicao": cod_requisicao
        }
        
        resposta_direta = fazer_requisicao_aplis("requisicaoListar", dat_direto)
        
        # Verificar se encontrou direto
        if resposta_direta.get("dat", {}).get("sucesso") == 1:
            lista_direta = resposta_direta.get("dat", {}).get("lista", [])
            if lista_direta and len(lista_direta) > 0:
                logger.info(f"[BuscarIntegrado] ✅ Requisição encontrada por busca direta!")
                dados_aplis = lista_direta[0]
                
                # LOG DETALHADO DOS DADOS BRUTOS DO apLIS
                logger.info(f"[BuscarIntegrado] 📋 DADOS BRUTOS DO apLIS:")
                logger.info(f"[BuscarIntegrado] 🔍 TODAS AS CHAVES RETORNADAS: {list(dados_aplis.keys())}")
                logger.info(f"[BuscarIntegrado] 🔍 DADOS COMPLETOS (JSON): {dados_aplis}")
                logger.info(f"[BuscarIntegrado]   - IdConvenio: {dados_aplis.get('IdConvenio')} (tipo: {type(dados_aplis.get('IdConvenio'))})")
                logger.info(f"[BuscarIntegrado]   - IdLocalOrigem: {dados_aplis.get('IdLocalOrigem')} (tipo: {type(dados_aplis.get('IdLocalOrigem'))})")
                logger.info(f"[BuscarIntegrado]   - IdFontePagadora: {dados_aplis.get('IdFontePagadora')} (tipo: {type(dados_aplis.get('IdFontePagadora'))})")
                logger.info(f"[BuscarIntegrado]   - NomeConvenio: {dados_aplis.get('NomeConvenio')}")
                logger.info(f"[BuscarIntegrado]   - NomeFontePagadora: {dados_aplis.get('NomeFontePagadora')}")
                logger.info(f"[BuscarIntegrado]   - NumGuiaConvenio: {dados_aplis.get('NumGuiaConvenio')}")
                logger.info(f"[BuscarIntegrado]   - NumExterno: {dados_aplis.get('NumExterno')}")
                
                # 🆕 BUSCAR VARIAÇÕES DO CAMPO (pode ter nome diferente)
                num_guia_variacoes = [
                    dados_aplis.get('NumGuiaConvenio'),
                    dados_aplis.get('NumExterno'),
                    dados_aplis.get('numGuiaConvenio'),
                    dados_aplis.get('numGuia'),
                    dados_aplis.get('GuiaConvenio'),
                    dados_aplis.get('NumGuia')
                ]
                logger.info(f"[BuscarIntegrado] 🎫 VARIAÇÕES DE NumGuia encontradas: {[v for v in num_guia_variacoes if v]}")
                
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
                                        logger.debug(f"[BuscarIntegrado][S3] Já em cache: {filename}")

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

                            logger.info(f"[BuscarIntegrado][S3] ✅ Encontradas {len(imagens)} imagens")
                        else:
                            logger.info(f"[BuscarIntegrado][S3] Nenhuma imagem em {caminho_s3_base}")

                    except Exception as e:
                        logger.error(f"[BuscarIntegrado][S3] Erro ao buscar imagens: {str(e)}")
                else:
                    logger.warning("[BuscarIntegrado][S3] Cliente S3 não disponível")

                # PASSO 3: 🆕 BUSCAR DADOS DO requisicaoResultado (SEMPRE tentar, independente do status)
                # ESTRATÉGIA: requisicaoListar é PRIMÁRIO (rápido, sem atraso)
                #             requisicaoResultado é COMPLEMENTO (convênio, local origem, etc.)
                dados_resultado = None
                status_exame = dados_aplis.get("StatusExame")  # 0=andamento, 1=concluído, 2=cancelado

                logger.info(f"[BuscarIntegrado] 📋 Tentando buscar dados complementares do requisicaoResultado...")
                dat_resultado = {"codRequisicao": cod_requisicao}
                resposta_resultado = fazer_requisicao_aplis("requisicaoResultado", dat_resultado)

                if resposta_resultado.get("dat", {}).get("sucesso") == 1:
                    dados_resultado = resposta_resultado.get("dat", {})
                    logger.info(f"[BuscarIntegrado] ✅ Dados complementares obtidos do requisicaoResultado!")
                    
                    # 🆕 LOG COMPLETO DO requisicaoResultado
                    logger.info(f"[BuscarIntegrado] 🔍 CHAVES DO requisicaoResultado: {list(dados_resultado.keys())}")
                    if dados_resultado.get("requisicao"):
                        logger.info(f"[BuscarIntegrado] 🔍 CHAVES DE requisicao: {list(dados_resultado['requisicao'].keys())}")
                        logger.info(f"[BuscarIntegrado] 🔍 DADOS COMPLETOS DE requisicao: {dados_resultado['requisicao']}")

                    # Extrair localOrigem do resultado
                    if dados_resultado.get("localOrigem"):
                        local_origem_resultado = dados_resultado["localOrigem"]
                        logger.info(f"[BuscarIntegrado] 🏥 Local de Origem: {local_origem_resultado.get('nome')}")

                    # Extrair convênio do resultado
                    if dados_resultado.get("paciente", {}).get("convenio"):
                        convenio_resultado = dados_resultado["paciente"]["convenio"]
                        logger.info(f"[BuscarIntegrado] 💳 Convênio: {convenio_resultado}")
                    
                    # Extrair NumGuia do resultado (se disponível) - BUSCAR EM VÁRIOS LUGARES
                    num_guia_resultado = None
                    
                    # Tentar várias localizações possíveis
                    if dados_resultado.get("requisicao"):
                        num_guia_resultado = (
                            dados_resultado["requisicao"].get("numGuia") or
                            dados_resultado["requisicao"].get("NumGuiaConvenio") or
                            dados_resultado["requisicao"].get("numGuiaConvenio") or
                            dados_resultado["requisicao"].get("GuiaConvenio") or
                            dados_resultado["requisicao"].get("NumExterno")
                        )
                    
                    if num_guia_resultado:
                        logger.info(f"[BuscarIntegrado] 🎫 NumGuia do resultado: {num_guia_resultado}")
                        # Atualizar dados_aplis se estiver vazio
                        if not dados_aplis.get("NumGuiaConvenio"):
                            dados_aplis["NumGuiaConvenio"] = num_guia_resultado
                            logger.info(f"[BuscarIntegrado] ✅ NumGuia atualizado de requisicaoResultado")
                    else:
                        logger.warning(f"[BuscarIntegrado] ⚠️ NumGuia não encontrado em requisicaoResultado")
                else:
                    logger.warning(f"[BuscarIntegrado] ⚠️ requisicaoResultado não disponível (StatusExame={status_exame})")
                    if status_exame == 0:
                        logger.info(f"[BuscarIntegrado] ℹ️ Requisição em andamento - dados complementares virão quando finalizar")

                # PASSO 3.5: 🆕 BUSCAR NumGuiaConvenio DIRETO DO BANCO (fallback se apLIS não retornar)
                num_guia_banco = None
                if not dados_aplis.get("NumGuiaConvenio") and not dados_aplis.get("NumExterno"):
                    logger.info(f"[BuscarIntegrado] 🔍 NumGuia vazio no apLIS, buscando no banco...")
                    try:
                        connection = pymysql.connect(**DB_CONFIG)
                        cursor = connection.cursor(pymysql.cursors.DictCursor)
                        
                        query = "SELECT NumGuiaConvenio, NumExterno FROM newdb.requisicao WHERE CodRequisicao = %s LIMIT 1"
                        logger.info(f"[BuscarIntegrado] 🔍 Query SQL: {query} (CodRequisicao={cod_requisicao})")
                        cursor.execute(query, (cod_requisicao,))
                        resultado_guia = cursor.fetchone()
                        
                        logger.info(f"[BuscarIntegrado] 🔍 Resultado SQL: {resultado_guia}")
                        
                        cursor.close()
                        connection.close()
                        
                        if resultado_guia:
                            num_guia_banco = resultado_guia.get("NumGuiaConvenio") or resultado_guia.get("NumExterno")
                            if num_guia_banco:
                                logger.info(f"[BuscarIntegrado] ✅ NumGuia encontrado no banco: {num_guia_banco}")
                                # Atualizar dados_aplis para usar depois
                                dados_aplis["NumGuiaConvenio"] = num_guia_banco
                            else:
                                logger.warning(f"[BuscarIntegrado] ⚠️ NumGuia também está vazio no banco (NumGuiaConvenio={resultado_guia.get('NumGuiaConvenio')}, NumExterno={resultado_guia.get('NumExterno')})")
                        else:
                            logger.warning(f"[BuscarIntegrado] ⚠️ Requisição {cod_requisicao} não encontrada no banco")
                    except Exception as e:
                        logger.error(f"[BuscarIntegrado] ❌ Erro ao buscar NumGuia no banco: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.info(f"[BuscarIntegrado] ℹ️ NumGuia já existe no apLIS, não buscando no banco")

                # PASSO 4: 🆕 BUSCAR DADOS COMPLETOS DO PACIENTE VIA API
                logger.info(f"[BuscarIntegrado] 📡 Buscando dados completos do paciente via API...")
                dados_sistema_antigo = None
                cod_paciente = dados_aplis.get("CodPaciente")
                
                # Confiar no CodPaciente retornado pela API
                logger.info(f"[BuscarIntegrado] ✅ Usando CodPaciente da API: {cod_paciente}")

                # 🔄 BUSCA HÍBRIDA: API primeiro, Banco SQL como fallback/complemento
                logger.info(f"[BuscarIntegrado] 🔄 Iniciando busca híbrida de dados do paciente...")
                
                # PRIORIDADE 1: Buscar via API (requisicaoResultado)
                dados_paciente_api = buscar_dados_paciente_via_api(cod_requisicao)
                
                # PRIORIDADE 2: Buscar no banco SQL (se necessário)
                dados_paciente_banco = None
                if cod_paciente:
                    dados_paciente_banco = buscar_dados_completos_paciente(cod_paciente)
                
                # 🔀 MESCLAR dados: API tem prioridade, banco complementa o que falta
                dados_finais = {}
                origem_dados = []
                
                if dados_paciente_api:
                    logger.info(f"[BuscarIntegrado] ✅ Dados da API disponíveis")
                    dados_finais.update(dados_paciente_api)
                    origem_dados.append("API")
                
                if dados_paciente_banco:
                    logger.info(f"[BuscarIntegrado] ✅ Dados do banco disponíveis")
                    # Complementar apenas campos que estão vazios/None
                    for campo, valor in dados_paciente_banco.items():
                        if campo != "origem" and (not dados_finais.get(campo) or dados_finais.get(campo) is None):
                            dados_finais[campo] = valor
                    if "BANCO_SQL" not in origem_dados:
                        origem_dados.append("BANCO_SQL")
                
                if dados_finais:
                    logger.info(f"[BuscarIntegrado] ✅ Dados mesclados! Origem: {' + '.join(origem_dados)}")
                    
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
                    
                    # Atualizar dados principais se disponíveis
                    if dados_finais.get("CPF"):
                        dados_aplis["CPF"] = dados_finais.get("CPF")
                    if dados_finais.get("NomPaciente"):
                        dados_aplis["NomPaciente"] = dados_finais.get("NomPaciente")
                else:
                    logger.warning(f"[BuscarIntegrado] ⚠️ Dados do paciente não encontrados (nem API nem banco)")
                    dados_sistema_antigo = None

                # PASSO 4: 🆕 BUSCAR IDs DO BANCO DE DADOS
                logger.info(f"[BuscarIntegrado] 🗄️ Buscando IDs do banco de dados MySQL...")
                ids_banco = buscar_ids_banco(cod_requisicao)

                # Sobrescrever IDs com os do banco (se disponíveis)
                # PRIORIDADE: Banco de dados > API apLIS
                if ids_banco.get("IdConvenio") is not None:
                    dados_aplis["IdConvenio"] = ids_banco["IdConvenio"]
                    logger.info(f"[BuscarIntegrado] ✅ IdConvenio do BANCO: {ids_banco['IdConvenio']}")

                if ids_banco.get("IdFontePagadora") is not None:
                    dados_aplis["IdFontePagadora"] = ids_banco["IdFontePagadora"]
                    logger.info(f"[BuscarIntegrado] ✅ IdFontePagadora do BANCO: {ids_banco['IdFontePagadora']}")

                if ids_banco.get("IdLocalOrigem") is not None:
                    dados_aplis["IdLocalOrigem"] = ids_banco["IdLocalOrigem"]
                    logger.info(f"[BuscarIntegrado] ✅ IdLocalOrigem do BANCO: {ids_banco['IdLocalOrigem']}")

                # PASSO 5: 🆕 ENRIQUECER COM DADOS DOS CSVs
                logger.info(f"[BuscarIntegrado] 🔍 Enriquecendo com dados dos CSVs...")

                # Buscar nome do médico no CSV
                nome_medico = None
                if dados_aplis.get("CRM") and dados_aplis.get("CRMUF"):
                    medico_csv = buscar_medico_por_crm(dados_aplis.get("CRM"), dados_aplis.get("CRMUF"))
                    if medico_csv:
                        nome_medico = medico_csv['nome']
                        logger.info(f"[BuscarIntegrado] ✅ Médico encontrado no CSV: {nome_medico}")
                    else:
                        logger.warning(f"[BuscarIntegrado] ⚠️ Médico CRM {dados_aplis.get('CRM')}/{dados_aplis.get('CRMUF')} não encontrado no CSV")

                # Buscar nome do convênio
                # PRIORIDADE 1: Se veio do requisicaoResultado, usar direto
                # PRIORIDADE 2: Buscar no CSV usando IdConvenio (agora do banco!)
                nome_convenio = None
                id_convenio = dados_aplis.get("IdConvenio")  # Agora vem do banco!

                if dados_resultado and dados_resultado.get("paciente", {}).get("convenio"):
                    nome_convenio = dados_resultado["paciente"]["convenio"]
                    logger.info(f"[BuscarIntegrado] ✅ Convênio do RESULTADO: {nome_convenio}")
                else:
                    if id_convenio:
                        nome_convenio = _buscar_convenio_nome(id_convenio)
                        logger.info(f"[BuscarIntegrado] 🔍 Convênio ID {id_convenio} → Nome: {nome_convenio}")

                # Buscar nome da fonte pagadora no CSV de instituições
                # IMPORTANTE: requisicaoListar NÃO retorna NomeFontePagadora, apenas IdFontePagadora
                nome_fonte_pagadora = None
                id_fonte_pagadora = dados_aplis.get("IdFontePagadora")
                if id_fonte_pagadora:
                    nome_fonte_pagadora = _buscar_instituicao_nome(id_fonte_pagadora)
                    logger.info(f"[BuscarIntegrado] 🔍 Fonte Pagadora ID {id_fonte_pagadora} → Nome: {nome_fonte_pagadora}")

                # Buscar nome do local de origem
                # PRIORIDADE 1: Se veio do requisicaoResultado, usar direto
                # PRIORIDADE 2: Buscar no CSV usando IdLocalOrigem
                nome_local_origem = None
                if dados_resultado and dados_resultado.get("localOrigem"):
                    nome_local_origem = dados_resultado["localOrigem"].get("nome")
                    logger.info(f"[BuscarIntegrado] ✅ Local Origem do RESULTADO: {nome_local_origem}")
                else:
                    id_local_origem = dados_aplis.get("IdLocalOrigem")
                    if id_local_origem:
                        nome_local_origem = _buscar_instituicao_nome(id_local_origem)
                        logger.info(f"[BuscarIntegrado] 🔍 Local Origem ID {id_local_origem} → Nome: {nome_local_origem}")
                    else:
                        logger.warning(f"[BuscarIntegrado] ⚠️ IdLocalOrigem não disponível e requisição não finalizada")

                # PASSO 4.5: VALIDAR CPF COM RECEITA FEDERAL
                logger.info(f"[BuscarIntegrado] 🔍 Validando CPF com Receita Federal...")
                validacao_cpf = validar_e_corrigir_dados_cpf(dados_aplis, dados_sistema_antigo)

                # Usar dados validados da Receita Federal (se disponível)
                nome_paciente_final = validacao_cpf["dados"]["nome"] or dados_aplis.get("NomPaciente")
                cpf_final = validacao_cpf["dados"]["cpf"] or dados_aplis.get("CPF")
                data_nasc_final = validacao_cpf["dados"]["dtaNasc"]

                # Se data de nascimento não veio da Receita, usar do sistema antigo
                if not data_nasc_final and dados_sistema_antigo:
                    data_nasc_final = dados_sistema_antigo.get("dtaNasc")

                # 🆕 PASSO 4.5.5: BUSCAR NO SUPABASE (HISTÓRICO)
                # Se data de nascimento ainda não foi encontrada, buscar no histórico do Supabase
                # (pode ter sido calculada a partir da idade em processamento anterior)
                if not data_nasc_final and SUPABASE_ENABLED:
                    try:
                        logger.info(f"[BuscarIntegrado] 🔍 Buscando data de nascimento no histórico Supabase...")
                        resultado_supabase = supabase_manager.buscar_requisicao(cod_requisicao)

                        if resultado_supabase.get('sucesso') == 1:
                            dados_supabase = resultado_supabase.get('dados', {})
                            data_nasc_supabase = dados_supabase.get('data_nascimento')

                            if data_nasc_supabase:
                                # Converter de YYYY-MM-DD para DD/MM/YYYY (formato esperado)
                                try:
                                    from datetime import datetime
                                    data_obj = datetime.strptime(data_nasc_supabase, '%Y-%m-%d')
                                    data_nasc_final = data_obj.strftime('%d/%m/%Y')
                                    logger.info(f"[BuscarIntegrado] ✅ Data de nascimento do Supabase: {data_nasc_final}")
                                except:
                                    data_nasc_final = data_nasc_supabase
                                    logger.info(f"[BuscarIntegrado] ✅ Data de nascimento do Supabase (formato direto): {data_nasc_final}")
                        else:
                            logger.debug(f"[BuscarIntegrado] Requisição não encontrada no Supabase")
                    except Exception as e:
                        logger.warning(f"[BuscarIntegrado] Erro ao buscar no Supabase: {e}")

                # PASSO 4.6: 🆕 BUSCAR REQUISIÇÃO CORRESPONDENTE (085 ↔ 0200)
                # Se esta requisição começa com 085 ou 0200, buscar dados do paciente da correspondente
                logger.info(f"[BuscarIntegrado] Verificando requisicao correspondente (085 <-> 0200)...")
                logger.info(f"[BuscarIntegrado] Codigo da requisicao para sincronizacao: {cod_requisicao}")

                # ESTRATÉGIA: Tentar banco primeiro (mais rápido), depois apLIS (fallback)
                req_correspondente = buscar_requisicao_correspondente(cod_requisicao)

                if not req_correspondente:
                    logger.info(f"[BuscarIntegrado] ⚠️ Não encontrada no banco, tentando buscar do apLIS...")
                    req_correspondente = buscar_requisicao_correspondente_aplis(cod_requisicao)

                logger.info(f"[BuscarIntegrado] Resultado da busca correspondente: {req_correspondente is not None}")

                if req_correspondente:
                    # PRIORIDADE: Dados da requisição correspondente > Sistema Antigo
                    # Isso garante que 085 e 0200 tenham EXATAMENTE os mesmos dados de paciente
                    logger.info(f"[BuscarIntegrado] 🔄 Sincronizando dados do paciente com requisição correspondente...")

                    # Se não tem nome ou CPF, usar da correspondente
                    if not nome_paciente_final and req_correspondente.get("NomePaciente"):
                        nome_paciente_final = req_correspondente["NomePaciente"]
                        logger.info(f"[BuscarIntegrado] ✅ Nome do paciente sincronizado: {nome_paciente_final}")

                    if not cpf_final and req_correspondente.get("CPF"):
                        cpf_final = req_correspondente["CPF"]
                        logger.info(f"[BuscarIntegrado] ✅ CPF sincronizado: {cpf_final}")

                    if not data_nasc_final and req_correspondente.get("DtaNasc"):
                        data_nasc_final = req_correspondente["DtaNasc"]
                        logger.info(f"[BuscarIntegrado] ✅ Data nascimento sincronizada: {data_nasc_final}")

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

                    # Endereço completo
                    dados_sistema_antigo["endereco"] = {
                        "cep": req_correspondente.get("CEP"),
                        "logradouro": req_correspondente.get("Logradouro"),
                        "numEndereco": req_correspondente.get("NumEndereco"),
                        "complemento": req_correspondente.get("Complemento"),
                        "bairro": req_correspondente.get("Bairro"),
                        "cidade": req_correspondente.get("Cidade"),
                        "uf": req_correspondente.get("UF")
                    }

                    logger.info(f"[BuscarIntegrado] ✅ Dados do paciente sincronizados com sucesso!")
                    logger.info(f"[BuscarIntegrado]    Sincronizados: RG, telefones, mae, estado civil, endereco completo, matricula convenio")

                # PASSO 5: Montar resposta ENRIQUECIDA com dados primários + complementares + sistema antigo + CSVs
                id_medico = dados_aplis.get("CodMedico")
                id_local_origem = dados_aplis.get("IdLocalOrigem")  # Definir aqui para uso posterior

                logger.debug(f"[BuscarIntegrado] IDs da requisição: convenio={id_convenio}, fonte={id_fonte_pagadora}, local={id_local_origem}, medico={id_medico}")
                logger.debug(f"[BuscarIntegrado] Nomes obtidos: convenio={nome_convenio}, fonte={nome_fonte_pagadora}, local={nome_local_origem}")
                
                # LOG: Verificar valor do numGuia antes de montar resposta
                num_guia_final = dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno") or (dados_sistema_antigo.get("numGuia") if dados_sistema_antigo else None)
                logger.info(f"[BuscarIntegrado] 🎫 NumGuia FINAL que será enviado: {num_guia_final}")
                logger.info(f"[BuscarIntegrado]    - NumGuiaConvenio (apLIS): {dados_aplis.get('NumGuiaConvenio')}")
                logger.info(f"[BuscarIntegrado]    - NumExterno (apLIS): {dados_aplis.get('NumExterno')}")
                logger.info(f"[BuscarIntegrado]    - numGuia (banco antigo): {dados_sistema_antigo.get('numGuia') if dados_sistema_antigo else 'N/A'}")
                
                resultado = {
                    "sucesso": 1,
                    # ===== DADOS PRIMÁRIOS (da busca direta) =====
                    "dados_primarios": {
                        "codRequisicao": dados_aplis.get("CodRequisicao"),
                        "idRequisicao": dados_aplis.get("IdRequisicao"),
                        "dtaColeta": dados_aplis.get("DtaColeta") or dados_aplis.get("DtaPrevista"),
                        "numGuia": dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno"),
                        "dadosClinicos": dados_aplis.get("IndicacaoClinica") or dados_aplis.get("NomExame")
                    },
                    # ===== DADOS DO PACIENTE (CPF é principal) =====
                    "paciente": {
                        "idPaciente": dados_aplis.get("CodPaciente"),
                        "nome": nome_paciente_final,  # ✅ PRIORIDADE: Receita Federal → apLIS
                        "cpf": cpf_final,  # ✅ PRIORIDADE: Receita Federal → apLIS

                        # 🆕 Dados do SISTEMA ANTIGO (se disponível) ou Receita Federal ou None (para OCR preencher)
                        "dtaNasc": data_nasc_final,  # ✅ PRIORIDADE: Receita Federal → Sistema Antigo
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
                    # ===== DADOS DO MÉDICO (enriquecido com CSV) =====
                    "medico": {
                        "idMedico": id_medico,
                        "crm": dados_aplis.get("CRM"),
                        "uf": dados_aplis.get("CRMUF"),
                        "nome": nome_medico  # ✅ Enriquecido do CSV
                    },
                    # ===== INFORMAÇÕES DE ORIGEM (enriquecidas com CSV) =====
                    "convenio": {
                        "id": id_convenio,  # ✅ ID do convênio
                        "nome": nome_convenio  # ✅ Vem do CSV via _buscar_convenio_nome()
                    },
                    "fontePagadora": {
                        "id": id_fonte_pagadora,  # ✅ ID da fonte pagadora
                        "nome": nome_fonte_pagadora  # ✅ Vem do CSV de instituições via _buscar_instituicao_nome()
                    },
                    "localOrigem": {
                        "id": id_local_origem,  # ✅ ID do local de origem
                        "nome": nome_local_origem  # ✅ Vem do CSV de instituições via _buscar_instituicao_nome()
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
                        "idConvenio": id_convenio,  # ✅ Com default
                        "idLocalOrigem": id_local_origem,  # ✅ Com default
                        "idFontePagadora": id_fonte_pagadora,  # ✅ Com default
                        "idMedico": id_medico  # ✅ Com default
                    },
                    # ===== METADATA =====
                    "origem": "busca_direta_por_codigo_enriquecida",
                    "statusIntegracao": "completo_dois_sistemas",
                    "avisos": [
                        f"✅ Sistema NOVO: codRequisicao, CPF, nome (tempo real - mesmo dia)",
                        f"✅ Sistema NOVO: médico, convênio, local origem, fonte pagadora",
                        f"{'✅ Sistema ANTIGO: dtaNasc, sexo, RG, telefone, endereço completo' if dados_sistema_antigo else '⚠️ Sistema ANTIGO: Dados não encontrados (paciente pode ser novo ou ter 1 dia de atraso)'}",
                        f"{'✅ RECEITA FEDERAL: Dados validados e corrigidos' if validacao_cpf.get('dados_corrigidos') else '✅ RECEITA FEDERAL: Dados conferem' if validacao_cpf.get('fonte_dados') == 'receita_federal' else '⚠️ RECEITA FEDERAL: Validação não disponível'}",
                        f"📋 OCR: Pode complementar/substituir dados se houver imagens"
                    ],
                    "sistemas_utilizados": {
                        "sistema_novo": "requisicaoListar (tempo real)",
                        "sistema_antigo": "admissaoListar (dados completos)" if dados_sistema_antigo else "não consultado",
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
                    # ===== SINCRONIZAÇÃO 0085 ↔ 0200 =====
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

                logger.info(f"[BuscarIntegrado] ✅ SUCESSO: {cod_requisicao} ({len(imagens)} imagens)")
                return jsonify(resultado), 200

        # Se não encontrou por busca direta, tentar com período amplo (FALLBACK)
        logger.warning(f"[BuscarIntegrado] Busca direta não retornou resultado, tentando com período amplo...")
        
        # PASSO 1 (FALLBACK): Obter dados primários + complementares usando a integração
        hoje = datetime.now()
        periodo_fim = hoje.strftime("%Y-%m-%d")
        periodo_ini = (hoje - timedelta(days=365)).strftime("%Y-%m-%d")

        resposta_integrada = listar_requisicoes_detalhadas(
            id_evento="50",
            periodo_ini=periodo_ini,
            periodo_fim=periodo_fim,
            enriquecer=True
        )

        # Verificar se encontrou a requisição
        if resposta_integrada.get("dat", {}).get("sucesso") != 1:
            logger.warning(f"[BuscarIntegrado] Requisição {cod_requisicao} não encontrada em nenhuma busca")
            return jsonify({
                "sucesso": 0,
                "erro": "Requisição não encontrada",
                "codRequisicao": cod_requisicao
            }), 404

        # PASSO 2: Buscar a requisição específica na lista integrada
        lista_requisicoes = resposta_integrada.get("dat", {}).get("lista", [])
        req_encontrada = None

        for req in lista_requisicoes:
            if req.get("dados_primarios", {}).get("codRequisicao") == cod_requisicao:
                req_encontrada = req
                break

        if not req_encontrada:
            logger.warning(f"[BuscarIntegrado] Código {cod_requisicao} não encontrado na lista integrada")
            return jsonify({
                "sucesso": 0,
                "erro": "Requisição não encontrada",
                "codRequisicao": cod_requisicao
            }), 404

        logger.info(f"[BuscarIntegrado] ✅ Requisição encontrada: {cod_requisicao}")

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
                                logger.debug(f"[BuscarIntegrado][S3] Já em cache: {filename}")

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

                    logger.info(f"[BuscarIntegrado][S3] ✅ Encontradas {len(imagens)} imagens")
                else:
                    logger.info(f"[BuscarIntegrado][S3] Nenhuma imagem em {caminho_s3_base}")

            except Exception as e:
                logger.error(f"[BuscarIntegrado][S3] Erro ao buscar imagens: {str(e)}")
        else:
            logger.warning("[BuscarIntegrado][S3] Cliente S3 não disponível")

        # PASSO 4: Montar resposta INTEGRADA com estrutura compatível com o frontend
        # Transformar dados integrados para formato esperado pelo frontend
        dados_primarios = req_encontrada.get("dados_primarios", {})
        dados_pac = req_encontrada.get("paciente", {})
        dados_med = req_encontrada.get("medico", {})
        dados_complementares = req_encontrada.get("dados_complementares", {})
        
        # Usar IDs conforme vêm da integração - os helpers tratarão None apropriadamente
        id_convenio_fallback = dados_complementares.get("idConvenio")
        id_local_origem_fallback = dados_complementares.get("idLocalOrigem")
        id_fonte_pagadora_fallback = dados_complementares.get("idFontePagadora")
        id_medico_fallback = dados_complementares.get("idMedico")
        
        logger.info(f"[BuscarIntegrado] 🔍 FALLBACK - IDs vindos da integração:")
        logger.info(f"[BuscarIntegrado]   - idConvenio: {id_convenio_fallback}")
        logger.info(f"[BuscarIntegrado]   - idLocalOrigem: {id_local_origem_fallback}")
        logger.info(f"[BuscarIntegrado]   - idFontePagadora: {id_fonte_pagadora_fallback}")
        logger.info(f"[BuscarIntegrado]   - idMedico: {id_medico_fallback}")
        logger.info(f"[BuscarIntegrado] 🔍 FALLBACK - Dados já enriquecidos da req_encontrada:")
        logger.info(f"[BuscarIntegrado]   - convenio: {req_encontrada.get('convenio')}")
        logger.info(f"[BuscarIntegrado]   - localOrigem: {req_encontrada.get('localOrigem')}")
        logger.info(f"[BuscarIntegrado]   - fontePagadora: {req_encontrada.get('fontePagadora')}")
        
        logger.debug(f"[BuscarIntegrado] IDs da integração: convenio={id_convenio_fallback}, fonte={id_fonte_pagadora_fallback}, local={id_local_origem_fallback}, medico={id_medico_fallback}")

        resultado = {
            "sucesso": 1,
            # ===== DADOS PRIMÁRIOS (da integração) =====
            "requisicao": {
                "codRequisicao": dados_primarios.get("codRequisicao"),
                "idRequisicao": dados_primarios.get("idRequisicao"),
                "dtaColeta": dados_primarios.get("dtaColeta"),
                "numGuia": dados_primarios.get("numGuia"),
                "dadosClinicos": dados_primarios.get("dadosClinicos"),
                # Dados complementares da integração (com defaults)
                "idConvenio": id_convenio_fallback,
                "idLocalOrigem": id_local_origem_fallback,
                "idFontePagadora": id_fonte_pagadora_fallback,
                "idMedico": id_medico_fallback,
                # Status da requisição no apLIS: 0=Em andamento, 1=Concluído, 2=Cancelado
                "StatusExame": status_exame
            },
            # ===== DADOS DO PACIENTE (CPF é principal - vem do requisicaoListar) =====
            "paciente": {
                "idPaciente": dados_pac.get("idPaciente"),
                "nome": dados_pac.get("nome"),
                "cpf": dados_pac.get("cpf"),  # ✅ PRINCIPAL - Vem do requisicaoListar
                # Dados que virão do OCR:
                "dtaNasc": dados_pac.get("dtaNasc"),
                "sexo": dados_pac.get("sexo"),
                "rg": dados_pac.get("rg"),
                "telCelular": dados_pac.get("telCelular"),
                "endereco": dados_pac.get("endereco", {})
            },
            # ===== DADOS DO MÉDICO (complementares) =====
            "medico": {
                "nome": dados_med.get("nome"),
                "crm": dados_med.get("crm"),
                "uf": dados_med.get("uf")
            },
            # ===== INFORMAÇÕES DE ORIGEM (complementares) =====
            "convenio": {
                "id": id_convenio_fallback,  # ✅ ID do convênio
                **req_encontrada.get("convenio", {})
            },
            "fontePagadora": {
                "id": id_fonte_pagadora_fallback,  # ✅ ID da fonte pagadora
                **req_encontrada.get("fontePagadora", {})
            },
            "localOrigem": {
                "id": id_local_origem_fallback,  # ✅ ID do local de origem
                **req_encontrada.get("localOrigem", {})
            },
            # ===== IMAGENS =====
            "imagens": imagens,
            "totalImagens": len(imagens),
            # ===== METADATA =====
            "origem": "requisicaoListar_integrado",
            "statusIntegracao": "completo",
            "avisos": [
                "Dados primários: codRequisicao, CPF, nome paciente - do apLIS",
                "Dados complementares: médico, convênio, local - enriquecidos",
                "Dados do paciente (dtaNasc, sexo, rg, endereço) - virão do OCR"
            ]
        }

        logger.info(f"[BuscarIntegrado] ✅ SUCESSO: {cod_requisicao} ({len(imagens)} imagens) - dados integrados retornados")
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"[BuscarIntegrado] ❌ Erro ao buscar requisição {cod_requisicao}: {str(e)}")
        import traceback
        logger.error(f"[BuscarIntegrado] Traceback: {traceback.format_exc()}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar requisição: {str(e)}"
        }), 500


@app.route('/api/debug/csv-dados', methods=['GET'])
def debug_csv_dados():
    """
    🧪 ENDPOINT DE DEBUG
    Retorna amostras dos dados carregados dos CSVs
    Útil para verificar se os CSVs foram carregados corretamente
    e quais IDs estão disponíveis
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
    🧪 ENDPOINT DE DEBUG/TESTE
    Lista os códigos de requisição disponíveis para testar
    Útil quando o usuário não sabe qual código buscar
    
    Requisição:
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
            # Usar padrão: últimos 30 dias
            hoje = datetime.now()
            periodo_fim = hoje.strftime("%Y-%m-%d")
            periodo_ini = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        
        logger.info(f"[Disponiveis] Listando códigos disponíveis: evento={id_evento}, período={periodo_ini} a {periodo_fim}")
        
        resposta = listar_requisicoes_detalhadas(id_evento, periodo_ini, periodo_fim, enriquecer=False)
        
        if resposta.get("dat", {}).get("sucesso") != 1:
            return jsonify({
                "sucesso": 0,
                "erro": "Erro ao buscar requisições"
            }), 500
        
        lista_requisicoes = resposta.get("dat", {}).get("lista", [])
        
        # Extrair códigos e pacientes
        codigos_disponiveis = []
        for req in lista_requisicoes[:limite]:
            codigos_disponiveis.append({
                "codigo": req.get("CodRequisicao"),
                "paciente": req.get("NomPaciente"),
                "cpf": req.get("CPF"),
                "data": req.get("DtaColeta") or req.get("DtaPrevista")
            })
        
        logger.info(f"[Disponiveis] Retornando {len(codigos_disponiveis)} códigos")
        
        return jsonify({
            "sucesso": 1,
            "total": len(lista_requisicoes),
            "codigos": codigos_disponiveis,
            "mensagem": f"Primeiros {len(codigos_disponiveis)} de {len(lista_requisicoes)} requisições disponíveis"
        }), 200
        
    except Exception as e:
        logger.error(f"[Disponiveis] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao listar requisições disponíveis: {str(e)}"
        }), 500


@app.route('/api/admissao/salvar', methods=['POST'])
def salvar_admissao():
    """
    Endpoint para salvar admissão
    """
    try:
        dados = request.json
        logger.info(f"[SalvarAdmissao] Iniciando salvamento. Dados recebidos: {json.dumps(dados, indent=2, ensure_ascii=False)[:1000]}")

        # 1. Sanitização de IDs (Top Level)
        campos_ids = ['idPaciente', 'idLaboratorio', 'idUnidade', 'idConvenio', 
                      'idLocalOrigem', 'idFontePagadora', 'idMedico', 'idExame']
        
        for campo in campos_ids:
            if campo in dados:
                if dados[campo] == "" or dados[campo] is None:
                    # Remover campos vazios opcionais para não enviar lixo
                    if campo not in ['idPaciente', 'idLaboratorio', 'idUnidade']: 
                        del dados[campo]
                else:
                    try:
                        dados[campo] = int(dados[campo])
                        # Se for 0 e opcional, remover (apLIS pode rejeitar ID 0 como chave estrangeira inválida)
                        if dados[campo] == 0 and campo not in ['idPaciente', 'idLaboratorio', 'idUnidade']:
                            del dados[campo]
                    except (ValueError, TypeError):
                        logger.warning(f"[SalvarAdmissao] Aviso: Campo {campo} não é numérico: {dados[campo]}")

        # 2. Sanitização de Data (dtaColeta)
        if 'dtaColeta' in dados and dados['dtaColeta']:
            # Remover hora se houver (apLIS espera YYYY-MM-DD)
            if 'T' in dados['dtaColeta']:
                dados['dtaColeta'] = dados['dtaColeta'].split('T')[0]
            elif ' ' in dados['dtaColeta']:
                dados['dtaColeta'] = dados['dtaColeta'].split(' ')[0]

        # 3. Sanitização de examesConvenio
        if 'examesConvenio' in dados and isinstance(dados['examesConvenio'], list):
            novos_exames = []
            for item in dados['examesConvenio']:
                if isinstance(item, dict):
                    # Se tem idExame, garante que é int
                    # Se for objeto, extrair APENAS o ID (apLIS espera lista de IDs simples, não objetos)
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
            
            # Se lista ficou vazia, remover chave para evitar erro de lista vazia (se apLIS não gostar)
            if not novos_exames:
                del dados['examesConvenio']
            else:
                # CRÍTICO: apLIS exige idExame na raiz para validação "Selecione o exame"
                # Usamos o primeiro exame da lista como principal
                dados['idExame'] = novos_exames[0]
        
        # Se veio apenas idExame na raiz e não tem lista, criar lista
        if 'idExame' in dados and 'examesConvenio' not in dados:
             dados['examesConvenio'] = [int(dados['idExame'])]

        # IMPORTANTE: NÃO remover idExame da raiz - o apLIS precisa TANTO do idExame
        # na raiz QUANTO da lista examesConvenio para funcionar corretamente

        # 🆕 4. Converter fontePagadora (nome) para idFontePagadora (ID) se necessário
        if 'fontePagadora' in dados and isinstance(dados['fontePagadora'], str):
            nome_fonte = dados['fontePagadora']
            logger.info(f"[SalvarAdmissao] 🔍 Recebido fontePagadora como nome: '{nome_fonte}'")
            logger.info(f"[SalvarAdmissao] 🔄 Buscando ID da instituição no cache...")
            
            instituicao = buscar_instituicao_por_nome(nome_fonte)
            if instituicao:
                dados['idFontePagadora'] = instituicao['id']
                logger.info(f"[SalvarAdmissao] ✅ Fonte pagadora convertida: '{nome_fonte}' → ID {instituicao['id']}")
                # Remover o campo de nome para não causar confusão
                del dados['fontePagadora']
            else:
                logger.warning(f"[SalvarAdmissao] ⚠️ Fonte pagadora '{nome_fonte}' não encontrada no cache")
                # Manter o campo para tentar usar default depois
                del dados['fontePagadora']

        # 5. Defaults e Limpeza (CAMPOS OBRIGATÓRIOS DO APLIS)
        if 'idLaboratorio' not in dados or not dados['idLaboratorio']:
            logger.info("[SalvarAdmissao] idLaboratorio não informado, usando default: 1")
            dados['idLaboratorio'] = 1

        if 'idUnidade' not in dados or not dados['idUnidade']:
            logger.info("[SalvarAdmissao] idUnidade não informada, usando default: 1")
            dados['idUnidade'] = 1

        # 🆕 VERIFICAR SE REQUISIÇÃO JÁ EXISTE (para evitar conflito de fonte pagadora)
        requisicao_existente = None
        if 'codRequisicao' in dados and dados['codRequisicao']:
            logger.info(f"[SalvarAdmissao] 🔍 Verificando se requisição {dados['codRequisicao']} já existe...")
            try:
                ids_banco = buscar_ids_banco(dados['codRequisicao'])
                if ids_banco and ids_banco.get('IdFontePagadora'):
                    requisicao_existente = ids_banco
                    logger.info(f"[SalvarAdmissao] ✅ Requisição existe! Fonte pagadora atual: {ids_banco.get('IdFontePagadora')}")
                    
                    # Se a fonte pagadora informada for diferente da cadastrada, usar a cadastrada
                    if 'idFontePagadora' in dados and dados['idFontePagadora'] != ids_banco.get('IdFontePagadora'):
                        logger.warning(f"[SalvarAdmissao] ⚠️ Conflito detectado!")
                        logger.warning(f"[SalvarAdmissao]   Fonte informada: {dados['idFontePagadora']}")
                        logger.warning(f"[SalvarAdmissao]   Fonte cadastrada: {ids_banco.get('IdFontePagadora')}")
                        logger.warning(f"[SalvarAdmissao]   🔄 Usando fonte pagadora já cadastrada para evitar erro do apLIS")
                        dados['idFontePagadora'] = ids_banco.get('IdFontePagadora')
                else:
                    logger.info(f"[SalvarAdmissao] ℹ️ Requisição não encontrada ou sem fonte pagadora - será nova requisição")
            except Exception as e:
                logger.error(f"[SalvarAdmissao] Erro ao verificar requisição existente: {e}")

        # CRÍTICO: apLIS exige convênio, fonte pagadora e médico (não podem ser null/0)
        # Se não foram informados, buscar IDs válidos do cache (preferencialmente PARTICULAR)
        if 'idConvenio' not in dados or not dados.get('idConvenio'):
            # Se requisição existe, usar convênio cadastrado
            if requisicao_existente and requisicao_existente.get('IdConvenio'):
                dados['idConvenio'] = requisicao_existente['IdConvenio']
                logger.info(f"[SalvarAdmissao] Usando convênio da requisição existente: {dados['idConvenio']}")
            else:
                id_convenio_default = obter_id_convenio_default()
                if id_convenio_default:
                    logger.info(f"[SalvarAdmissao] idConvenio não informado, usando default: {id_convenio_default}")
                    dados['idConvenio'] = id_convenio_default
                else:
                    logger.error("[SalvarAdmissao] ❌ Cache de convênios vazio! Não é possível salvar sem convênio.")
                    return jsonify({
                        "sucesso": 0,
                        "erro": "Convênio não informado e cache de convênios vazio. Configure os dados no sistema."
                    }), 400

        if 'idFontePagadora' not in dados or not dados.get('idFontePagadora'):
            # Se requisição existe, usar fonte pagadora cadastrada
            if requisicao_existente and requisicao_existente.get('IdFontePagadora'):
                dados['idFontePagadora'] = requisicao_existente['IdFontePagadora']
                logger.info(f"[SalvarAdmissao] Usando fonte pagadora da requisição existente: {dados['idFontePagadora']}")
            else:
                id_instituicao_default = obter_id_instituicao_default()
            if id_instituicao_default:
                logger.info(f"[SalvarAdmissao] idFontePagadora não informada, usando default: {id_instituicao_default}")
                dados['idFontePagadora'] = id_instituicao_default
            else:
                logger.error("[SalvarAdmissao] ❌ Cache de instituições vazio! Não é possível salvar sem fonte pagadora.")
                return jsonify({
                    "sucesso": 0,
                    "erro": "Fonte pagadora não informada e cache de instituições vazio. Configure os dados no sistema."
                }), 400

        if 'idMedico' not in dados or not dados.get('idMedico'):
            id_medico_default = obter_id_medico_default()
            if id_medico_default:
                logger.info(f"[SalvarAdmissao] idMedico não informado, usando default: {id_medico_default}")
                dados['idMedico'] = id_medico_default
            else:
                logger.error("[SalvarAdmissao] ❌ Cache de médicos vazio! Não é possível salvar sem médico.")
                return jsonify({
                    "sucesso": 0,
                    "erro": "Médico não informado e cache de médicos vazio. Configure os dados no sistema."
                }), 400

        if 'codRequisicao' in dados and not dados['codRequisicao']:
            del dados['codRequisicao']

        # 🆕 VALIDAR numGuia (deve ter exatamente 9 dígitos válidos)
        # IMPORTANTE: Para alguns convênios/procedimentos, o numGuia é OBRIGATÓRIO
        # Se não tiver, o apLIS pode rejeitar dependendo do tipo de exame
        tem_num_guia_valido = False
        if 'numGuia' in dados:
            logger.info(f"[SalvarAdmissao] 🔍 Campo numGuia recebido: '{dados['numGuia']}' (tipo: {type(dados['numGuia'])})")
            num_guia = str(dados['numGuia']).strip()
            # Remover caracteres não numéricos
            num_guia_limpo = ''.join(filter(str.isdigit, num_guia))
            
            logger.info(f"[SalvarAdmissao] 🔍 numGuia após limpeza: '{num_guia_limpo}' (tamanho: {len(num_guia_limpo)})")
            
            # Só aceita se tiver exatamente 9 dígitos E não for só zeros
            if num_guia_limpo and len(num_guia_limpo) == 9 and num_guia_limpo != '000000000':
                # Válido - manter
                dados['numGuia'] = num_guia_limpo
                tem_num_guia_valido = True
                logger.info(f"[SalvarAdmissao] ✅ numGuia válido, será enviado: {num_guia_limpo}")
            else:
                # Inválido - remover
                del dados['numGuia']
                logger.warning(f"[SalvarAdmissao] ⚠️ numGuia inválido ou vazio ('{num_guia_limpo}'), campo removido")
                logger.warning(f"[SalvarAdmissao] ⚠️ ATENÇÃO: Se o apLIS rejeitar, pode ser porque o numGuia é obrigatório para este convênio/exame")
        else:
            logger.warning(f"[SalvarAdmissao] ⚠️ Campo numGuia não presente nos dados recebidos")
            logger.warning(f"[SalvarAdmissao] ⚠️ Alguns convênios exigem número da guia. Se o apLIS rejeitar, preencha o campo 'Número da Guia'")

        # 🆕 GERAR numGuia PROVISÓRIO se não tiver (previne erro do apLIS)
        # Alguns procedimentos (ex: patologia molecular) EXIGEM numGuia obrigatoriamente
        # Solução: usar os últimos 9 dígitos do código da requisição como número da guia
        if not tem_num_guia_valido and 'codRequisicao' in dados and dados['codRequisicao']:
            cod_req_limpo = ''.join(filter(str.isdigit, str(dados['codRequisicao'])))
            if len(cod_req_limpo) >= 9:
                # Pegar últimos 9 dígitos
                num_guia_provisorio = cod_req_limpo[-9:]
                dados['numGuia'] = num_guia_provisorio
                logger.info(f"[SalvarAdmissao] 🔄 numGuia gerado automaticamente (últimos 9 dígitos): {num_guia_provisorio}")
                logger.info(f"[SalvarAdmissao] 💡 Baseado no código da requisição: {dados['codRequisicao']}")
            else:
                # Código muito curto, usar com zeros à esquerda
                num_guia_provisorio = cod_req_limpo.zfill(9)[-9:]
                dados['numGuia'] = num_guia_provisorio
                logger.info(f"[SalvarAdmissao] 🔄 numGuia gerado (código curto, com padding): {num_guia_provisorio}")

        # 🆕 LIMPAR campos vazios (apLIS rejeita strings vazias)
        # Remover campos que estão vazios para evitar erros de validação
        campos_para_limpar = ['matConvenio', 'fontePagadora', 'dadosClinicos']
        for campo in campos_para_limpar:
            if campo in dados and (dados[campo] == '' or dados[campo] is None):
                logger.warning(f"[SalvarAdmissao] ⚠️ Campo '{campo}' está vazio, removendo do payload")
                del dados[campo]

        # Validar idPaciente > 0 (se fornecido)
        if 'idPaciente' in dados and (not isinstance(dados['idPaciente'], int) or dados['idPaciente'] <= 0):
             return jsonify({
                "sucesso": 0,
                "erro": f"ID do Paciente inválido: {dados.get('idPaciente')}"
            }), 400

        # 🆕 SE NÃO TEM idPaciente, tentar buscar/criar pelo CPF
        if 'idPaciente' not in dados or dados.get('idPaciente') is None or dados.get('idPaciente') == '':
            logger.warning("[SalvarAdmissao] ⚠️ idPaciente não fornecido - tentando buscar/criar paciente pelo CPF")

            # Verificar se temos CPF para buscar (aceitar vários formatos)
            cpf_paciente = dados.get('cpf') or dados.get('NumCPF') or dados.get('CPF')
            nome_paciente = dados.get('nome') or dados.get('nomePaciente') or dados.get('NomPaciente')
            data_nascimento = dados.get('dataNascimento') or dados.get('dtaNasc') or dados.get('DtaNasc') or dados.get('DtaNascimento')

            if not cpf_paciente:
                logger.error("[SalvarAdmissao] ❌ Dados do paciente não fornecidos!")
                logger.error(f"[SalvarAdmissao] ❌ Campos recebidos: {list(dados.keys())}")
                logger.error(f"[SalvarAdmissao] ❌ Valores: cpf={dados.get('cpf')}, NumCPF={dados.get('NumCPF')}, CPF={dados.get('CPF')}")
                return jsonify({
                    "sucesso": 0,
                    "erro": "idPaciente não informado e CPF não encontrado nos dados recebidos. O frontend deve enviar 'cpf', 'NumCPF' ou 'CPF' junto com 'nome'/'NomPaciente' para criar novo paciente."
                }), 400

            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf_paciente))
            logger.info(f"[SalvarAdmissao] 🔍 Buscando paciente por CPF: {cpf_limpo}")

            # 1. BUSCAR PACIENTE NO BANCO
            try:
                connection = pymysql.connect(**DB_CONFIG)
                with connection.cursor() as cursor:
                    query = "SELECT CodPaciente, NomPaciente FROM newdb.paciente WHERE CPF = %s LIMIT 1"
                    cursor.execute(query, (cpf_limpo,))
                    resultado = cursor.fetchone()

                    if resultado:
                        # Paciente encontrado!
                        cod_paciente = resultado[0]
                        nome_encontrado = resultado[1]
                        logger.info(f"[SalvarAdmissao] ✅ Paciente encontrado! ID: {cod_paciente} - {nome_encontrado}")
                        dados['idPaciente'] = cod_paciente
                        connection.close()
                    else:
                        # Paciente NÃO encontrado - precisa criar
                        connection.close()
                        logger.warning(f"[SalvarAdmissao] ⚠️ Paciente com CPF {cpf_limpo} não encontrado no banco")

                        # Verificar se temos dados mínimos para criar
                        if not nome_paciente:
                            return jsonify({
                                "sucesso": 0,
                                "erro": "Paciente não encontrado no sistema e nome não foi fornecido. Impossível criar novo cadastro."
                            }), 400

                        # 2. VALIDAR CPF NA RECEITA FEDERAL
                        logger.info(f"[SalvarAdmissao] 🔍 Validando CPF {cpf_limpo} na Receita Federal...")
                        dados_receita = consultar_cpf_receita_federal(cpf_limpo, data_nascimento)

                        usa_metodo_sem_cpf = False
                        
                        if not dados_receita or not dados_receita.get('valido'):
                            logger.warning(f"[SalvarAdmissao] ⚠️ CPF {cpf_limpo} não validado pela Receita Federal")
                            logger.info(f"[SalvarAdmissao] 🔄 Usando método alternativo: Paciente sem documento (CPF não validado)")
                            usa_metodo_sem_cpf = True
                            
                            # Marcar que está usando método alternativo para retornar aviso ao frontend
                            dados['_aviso_metodo_alternativo'] = True
                            dados['_cpf_nao_validado'] = cpf_limpo
                        else:
                            logger.info(f"[SalvarAdmissao] ✅ CPF validado pela Receita Federal!")
                            logger.info(f"[SalvarAdmissao]   Nome na RF: {dados_receita.get('nome')}")

                        # 3. CRIAR PACIENTE NO apLIS
                        if usa_metodo_sem_cpf:
                            logger.info(f"[SalvarAdmissao] 📝 Criando novo paciente com método 'Sem Documento'...")
                            logger.warning(f"[SalvarAdmissao] ⚠️ ATENÇÃO: CPF {cpf_limpo} NÃO FOI VALIDADO na Receita Federal - usando cpfAusente")
                        else:
                            logger.info(f"[SalvarAdmissao] 📝 Criando novo paciente no sistema...")
                        
                        dat_paciente = {
                            "idEvento": "3",  # Evento de inclusão de paciente
                            "nome": nome_paciente
                        }
                        
                        # Se CPF foi validado, enviar CPF. Se não, usar cpfAusente
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
                        logger.info(f"[SalvarAdmissao] 📤 Enviando para apLIS pacienteSalvar:")
                        logger.info(f"[SalvarAdmissao]   Dados: {json.dumps(dat_paciente, indent=2, ensure_ascii=False)}")

                        # Chamar apLIS para criar
                        resposta_paciente = fazer_requisicao_aplis("pacienteSalvar", dat_paciente)
                        
                        # Log completo da resposta para debug
                        logger.info(f"[SalvarAdmissao] 📋 Resposta completa do apLIS pacienteSalvar:")
                        logger.info(f"[SalvarAdmissao]   JSON: {json.dumps(resposta_paciente, indent=2, ensure_ascii=False)}")

                        # Verificar se apLIS retornou resposta válida
                        if not resposta_paciente:
                            logger.error(f"[SalvarAdmissao] ❌ apLIS não retornou resposta (None ou vazio)")
                            return jsonify({
                                "sucesso": 0,
                                "erro": "Erro ao criar novo paciente: apLIS não retornou resposta"
                            }), 500
                        
                        if resposta_paciente.get("dat", {}).get("sucesso") == 1:
                            # Tentar múltiplos campos possíveis para o ID do paciente
                            dat = resposta_paciente.get("dat", {})
                            novo_id = dat.get("codPaciente") or dat.get("idPaciente") or dat.get("CodPaciente") or dat.get("IdPaciente") or dat.get("id")
                            
                            logger.info(f"[SalvarAdmissao] 📋 Campos disponíveis na resposta 'dat': {list(dat.keys())}")
                            logger.info(f"[SalvarAdmissao] 📋 Valores dos campos: {json.dumps(dat, ensure_ascii=False)}")
                            
                            if not novo_id:
                                logger.error(f"[SalvarAdmissao] ❌ apLIS retornou sucesso mas não encontrou ID do paciente em nenhum campo esperado")
                                logger.error(f"[SalvarAdmissao] ❌ Campos tentados: codPaciente, idPaciente, CodPaciente, IdPaciente, id")
                                logger.error(f"[SalvarAdmissao] ❌ Resposta completa dat: {json.dumps(dat, ensure_ascii=False)}")
                                return jsonify({
                                    "sucesso": 0,
                                    "erro": f"Erro ao criar novo paciente: apLIS retornou sucesso mas não retornou ID do paciente. Campos disponíveis: {list(dat.keys())}"
                                }), 500
                            
                            logger.info(f"[SalvarAdmissao] ✅ Paciente criado com sucesso! ID: {novo_id}")
                            dados['idPaciente'] = novo_id
                        else:
                            erro_msg = resposta_paciente.get("dat", {}).get("msg") or resposta_paciente.get("dat", {}).get("msgErro") or resposta_paciente.get("msg") or "Erro desconhecido"
                            cod_erro = resposta_paciente.get("dat", {}).get("codErro")
                            logger.error(f"[SalvarAdmissao] ❌ Erro ao criar paciente:")
                            logger.error(f"[SalvarAdmissao]   Mensagem: {erro_msg}")
                            logger.error(f"[SalvarAdmissao]   Código erro: {cod_erro}")
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

        # Validar campos MÍNIMOS obrigatórios (conforme API apLIS admissaoSalvar)
        campos_obrigatorios = [
            'idPaciente',    # ID do paciente no sistema
            'dtaColeta',     # Data da coleta
            'idLaboratorio', # ID do laboratório
            'idUnidade'      # ID da unidade
        ]

        # Campos opcionais mas recomendados (API aceita sem eles)
        # idConvenio, idLocalOrigem, idFontePagadora, idMedico,
        # idExame, examesConvenio, dadosClinicos, numGuia

        campos_faltantes = [campo for campo in campos_obrigatorios if campo not in dados or dados[campo] is None]

        if campos_faltantes:
            erro_msg = f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}"
            logger.warning(f"[SalvarAdmissao] ❌ {erro_msg}")
            return jsonify({
                "sucesso": 0,
                "erro": erro_msg
            }), 400

        logger.info(f"[SalvarAdmissao] Dados finais para apLIS: {json.dumps(dados, indent=2, ensure_ascii=False)[:1000]}")
        logger.info(f"[SalvarAdmissao] 🎫 Campo numGuia no envio: {'PRESENTE (' + str(dados.get('numGuia')) + ')' if 'numGuia' in dados else 'AUSENTE (não será enviado)'}")
        logger.info(f"[SalvarAdmissao] 🔍 Campos completos enviados:")
        logger.info(f"[SalvarAdmissao]   - codRequisicao: {dados.get('codRequisicao')}")
        logger.info(f"[SalvarAdmissao]   - idPaciente: {dados.get('idPaciente')}")
        logger.info(f"[SalvarAdmissao]   - idMedico: {dados.get('idMedico')}")
        logger.info(f"[SalvarAdmissao]   - idLocalOrigem: {dados.get('idLocalOrigem')}")
        logger.info(f"[SalvarAdmissao]   - dtaColeta: {dados.get('dtaColeta')}")
        logger.info(f"[SalvarAdmissao]   - examesConvenio: {dados.get('examesConvenio')}")

        # Chamar apLIS
        resultado = salvar_admissao_aplis(dados)

        if resultado.get("dat", {}).get("sucesso") == 1:
            cod_requisicao = resultado["dat"].get("codRequisicao")
            logger.info(f"[SalvarAdmissao] ✅ Sucesso! CodRequisicao: {cod_requisicao}")

            # 🆕 ATUALIZAR STATUS NO SUPABASE PARA "SALVO"
            if SUPABASE_ENABLED and cod_requisicao:
                try:
                    logger.info(f"[SalvarAdmissao] 💾 Atualizando status no Supabase: {cod_requisicao}")

                    # Buscar dados existentes no Supabase
                    resultado_busca = supabase_manager.buscar_requisicao(cod_requisicao)

                    if resultado_busca.get('sucesso') == 1:
                        # Requisição já existe, atualizar status
                        dados_existentes = resultado_busca['dados']

                        # Atualizar apenas o status para "salvo"
                        dados_update = {
                            **dados_existentes,
                            'status': 'salvo',
                            'processado_por': 'sistema_admissao'
                        }

                        # Salvar novamente (irá fazer UPDATE)
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
                            logger.info(f"[SalvarAdmissao] ✅ Status atualizado no Supabase!")
                        else:
                            logger.warning(f"[SalvarAdmissao] ⚠️ Erro ao atualizar Supabase: {resultado_save.get('erro')}")
                    else:
                        logger.info(f"[SalvarAdmissao] ℹ️ Requisição não encontrada no Supabase (não foi processada via OCR)")

                except Exception as e:
                    logger.warning(f"[SalvarAdmissao] ⚠️ Erro ao atualizar Supabase (continuando): {str(e)}")

            # 🆕 CRIAR REQUISIÇÃO CORRESPONDENTE (0085 ↔ 0200)
            cod_correspondente = None
            if cod_requisicao and (cod_requisicao.startswith('0085') or cod_requisicao.startswith('0200')):
                try:
                    tipo_atual = '0085' if cod_requisicao.startswith('0085') else '0200'
                    tipo_correspondente = '0200' if tipo_atual == '0085' else '0085'
                    cod_correspondente = tipo_correspondente + cod_requisicao[4:]
                    
                    logger.info(f"[SalvarAdmissao] 🔄 Criando requisição correspondente: {cod_correspondente}")
                    
                    # Copiar todos os dados da requisição original
                    dados_correspondente = dados.copy()
                    
                    # Ajustar campos específicos se necessário
                    # O codRequisicao será o correspondente
                    dados_correspondente['codRequisicao'] = cod_correspondente
                    
                    # Chamar apLIS para criar a correspondente
                    resultado_correspondente = salvar_admissao_aplis(dados_correspondente)
                    
                    if resultado_correspondente.get("dat", {}).get("sucesso") == 1:
                        logger.info(f"[SalvarAdmissao] ✅ Requisição correspondente criada: {cod_correspondente}")
                    else:
                        erro_msg = resultado_correspondente.get("dat", {}).get("msg") or "Erro desconhecido"
                        logger.warning(f"[SalvarAdmissao] ⚠️ Erro ao criar requisição correspondente: {erro_msg}")
                        logger.warning(f"[SalvarAdmissao] ⚠️ Resposta: {json.dumps(resultado_correspondente, ensure_ascii=False)}")
                        
                except Exception as e:
                    logger.error(f"[SalvarAdmissao] ❌ Erro ao criar requisição correspondente: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Preparar resposta com aviso se usou método alternativo
            resposta = {
                "sucesso": 1,
                "mensagem": "Admissão salva com sucesso!",
                "codRequisicao": cod_requisicao,
                "dados": resultado["dat"]
            }
            
            # Adicionar código da correspondente se foi criada
            if cod_correspondente:
                resposta["codRequisicaoCorrespondente"] = cod_correspondente
                resposta["mensagem"] = f"Admissão salva com sucesso! (Principal: {cod_requisicao}, Correspondente: {cod_correspondente})"
            
            # Adicionar aviso se CPF não foi validado
            if dados.get('_aviso_metodo_alternativo'):
                cpf_nao_validado = dados.get('_cpf_nao_validado', 'não informado')
                resposta["aviso"] = {
                    "tipo": "cpf_nao_validado",
                    "mensagem": f"⚠️ ATENÇÃO: Paciente cadastrado com método alternativo (CPF {cpf_nao_validado} não foi validado na Receita Federal). Verifique os dados do paciente.",
                    "cpf": cpf_nao_validado
                }
                logger.warning(f"[SalvarAdmissao] ⚠️ Retornando aviso de CPF não validado: {cpf_nao_validado}")

            return jsonify(resposta), 200
        else:
            # Tentar extrair erro de vários lugares (topo ou dentro de dat)
            erro_aplis = resultado.get("erro")
            msg_aplis = resultado.get("msg")
            cod_erro = resultado.get("dat", {}).get("codErro") if isinstance(resultado.get("dat"), dict) else None
            msg_erro = resultado.get("dat", {}).get("msgErro") if isinstance(resultado.get("dat"), dict) else None
            
            # Se não tem erro no topo, procurar dentro de 'dat'
            if not erro_aplis and not msg_aplis:
                dat = resultado.get("dat", {})
                if isinstance(dat, dict):
                    erro_aplis = dat.get("erro") or dat.get("mensagem") or dat.get("msg") or msg_erro
            
            if not erro_aplis:
                # Se não encontrou erro legível, retornar o dump do objeto para debug
                erro_aplis = f"Erro não identificado no retorno do apLIS: {json.dumps(resultado, ensure_ascii=False)}"
            
            # Se for erro de numGuia, adicionar informação de debug
            if "Guia Convênio" in str(erro_aplis) or "numGuia" in str(erro_aplis):
                num_guia_enviado = dados.get('numGuia', 'NÃO ENVIADO')
                erro_aplis = (
                    f"❌ {erro_aplis}\n\n"
                    f"🔍 DEBUG: numGuia enviado = '{num_guia_enviado}' (tamanho: {len(str(num_guia_enviado)) if num_guia_enviado != 'NÃO ENVIADO' else 0})\n\n"
                    f"💡 CAUSA: O convênio/procedimento selecionado EXIGE o número da guia (9 dígitos).\n\n"
                    f"🔧 SOLUÇÃO:\n"
                    f"  1. Localize o campo 'Número da Guia' no formulário (lado direito)\n"
                    f"  2. Preencha com 9 dígitos numéricos (ex: 123456789)\n"
                    f"  3. Tente salvar novamente\n\n"
                    f"📝 ALTERNATIVA: Se não tiver o número da guia:\n"
                    f"  - Entre em contato com o convênio para obter\n"
                    f"  - Ou use '000000001' como número provisório"
                )
            
            # Se for erro de fonte pagadora conflitante, adicionar explicação
            if "fonte pagadora" in str(erro_aplis).lower() or "procedimentos cobrados" in str(erro_aplis).lower():
                logger.error(f"[SalvarAdmissao] 🔍 ERRO DE FONTE PAGADORA DETECTADO")
                logger.error(f"[SalvarAdmissao]   Fonte pagadora enviada: {dados.get('idFontePagadora')}")
                logger.error(f"[SalvarAdmissao]   Convênio enviado: {dados.get('idConvenio')}")
                logger.error(f"[SalvarAdmissao]   Código requisição: {dados.get('codRequisicao')}")
                
                # Adicionar dica de solução
                erro_aplis = (
                    f"{erro_aplis}\n\n"
                    f"💡 CAUSA: A requisição já existe no sistema com outra fonte pagadora. "
                    f"O apLIS não permite alterar a fonte pagadora de uma requisição existente.\n\n"
                    f"🔧 SOLUÇÃO: O sistema tentará usar automaticamente a fonte pagadora já cadastrada. "
                    f"Recarregue a página e tente novamente."
                )
            
            msg_final = f"{erro_aplis} {msg_aplis or ''}".strip()
            logger.error(f"[SalvarAdmissao] ❌ ERRO DO apLIS: {msg_final}")
            logger.error(f"[SalvarAdmissao] ❌ CodErro: {cod_erro}, MsgErro: {msg_erro}")
            logger.error(f"[SalvarAdmissao] ❌ Resposta completa: {json.dumps(resultado, ensure_ascii=False)}")
            return jsonify({
                "sucesso": 0,
                "erro": msg_final,
                "detalhes": resultado
            }), 400

    except Exception as e:
        logger.error(f"[SalvarAdmissao] 💥 Erro exceção: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro no servidor: {str(e)}"
        }), 500


@app.route('/api/convenios/buscar-por-nome', methods=['POST'])
def buscar_convenio_por_nome():
    """
    Busca convênio por nome (para preencher ID quando OCR encontra carteirinha)
    """
    try:
        dados = request.json
        nome_convenio = dados.get('nome_convenio', '').strip().upper()

        if not nome_convenio:
            return jsonify({
                "sucesso": 0,
                "erro": "Nome do convênio não fornecido"
            }), 400

        logger.info(f"[CONVENIO] Procurando convênio: {nome_convenio}")

        # Buscar no cache de convênios carregado
        for id_convenio, convenio_data in CONVENIOS_CACHE.items():
            if convenio_data.get('nome', '').strip().upper() == nome_convenio:
                logger.info(f"[CONVENIO] ✅ Encontrado: ID={id_convenio}, Nome={convenio_data.get('nome')}")
                return jsonify({
                    "sucesso": 1,
                    "idConvenio": int(id_convenio),
                    "nomeConvenio": convenio_data.get('nome')
                }), 200

        # Se não encontrará exato, tentar busca parcial (contém)
        for id_convenio, convenio_data in CONVENIOS_CACHE.items():
            if nome_convenio in convenio_data.get('nome', '').strip().upper():
                logger.info(f"[CONVENIO] ✅ Encontrado (busca parcial): ID={id_convenio}, Nome={convenio_data.get('nome')}")
                return jsonify({
                    "sucesso": 1,
                    "idConvenio": int(id_convenio),
                    "nomeConvenio": convenio_data.get('nome')
                }), 200

        logger.warning(f"[CONVENIO] ❌ Convênio não encontrado: {nome_convenio}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Convênio '{nome_convenio}' não encontrado"
        }), 404

    except Exception as e:
        logger.error(f"[CONVENIO] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar convênio: {str(e)}"
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
                erros.append("Data de coleta inválida. Use formato YYYY-MM-DD")

        # Validar IDs positivos
        campos_id = ['idLaboratorio', 'idUnidade', 'idPaciente', 'idConvenio',
                     'idLocalOrigem', 'idFontePagadora', 'idMedico', 'idExame']

        for campo in campos_id:
            if campo in dados and (not isinstance(dados[campo], int) or dados[campo] <= 0):
                erros.append(f"{campo} deve ser um número inteiro positivo")

        # Validar array de exames
        if 'examesConvenio' in dados:
            if not isinstance(dados['examesConvenio'], list) or len(dados['examesConvenio']) == 0:
                erros.append("examesConvenio deve ser um array com pelo menos um exame")

        # Avisos
        if 'numGuia' not in dados:
            avisos.append("Número da guia não informado")

        if 'dadosClinicos' not in dados:
            avisos.append("Dados clínicos não informados")

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
                "mensagem": "CPF não informado"
            }), 400

        logger.info(f"[ValidarCPF] Recebida solicitação de validação: CPF={cpf}")
        logger.info(f"[ValidarCPF] Dados do OCR: Nome='{nome_ocr}', Data Nasc='{data_nascimento_ocr}'")

        # Consultar Receita Federal
        dados_receita = consultar_cpf_receita_federal(cpf, data_nascimento or data_nascimento_ocr)

        if dados_receita:
            logger.info(f"[ValidarCPF] ✅ CPF validado com sucesso: {dados_receita.get('nome')}")
            
            # Preparar comparação de dados
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
                    "divergente": False  # CPF sempre será igual (usado para buscar)
                },
                "data_nascimento": {
                    "sistema": data_nascimento_ocr,
                    "receita_federal": dados_receita.get('data_nascimento', ''),
                    "divergente": bool(data_nascimento_ocr and dados_receita.get('data_nascimento') and
                                      data_nascimento_ocr.replace('/', '').replace('-', '') != 
                                      dados_receita.get('data_nascimento', '').replace('/', '').replace('-', ''))
                }
            }
            
            logger.info(f"[ValidarCPF] 📊 Comparação preparada:")
            logger.info(f"[ValidarCPF]   Nome: '{comparacao['nome']['sistema']}' vs '{comparacao['nome']['receita_federal']}' (divergente: {comparacao['nome']['divergente']})")
            logger.info(f"[ValidarCPF]   Data: '{comparacao['data_nascimento']['sistema']}' vs '{comparacao['data_nascimento']['receita_federal']}' (divergente: {comparacao['data_nascimento']['divergente']})")
            
            return jsonify({
                "sucesso": 1,
                "mensagem": "CPF validado com sucesso",
                "dados_receita_federal": dados_receita,
                "comparacao": comparacao
            }), 200
        else:
            logger.warning(f"[ValidarCPF] ❌ Não foi possível validar o CPF")
            return jsonify({
                "sucesso": 0,
                "mensagem": "Não foi possível validar o CPF na Receita Federal"
            }), 400

    except Exception as e:
        logger.error(f"[ValidarCPF] 💥 Erro ao validar CPF: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "mensagem": f"Erro ao validar CPF: {str(e)}"
        }), 500


@app.route('/', methods=['GET'])
def index():
    """
    Página inicial - informações da API
    """
    return jsonify({
        "nome": "API de Admissão - Sistema Lab",
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
        "documentacao": "Veja README.md para mais informações",
        "nota": "API agora usa metodologia requisicaoListar do apiaplisreduzido"
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check do servidor
    """
    return jsonify({
        "status": "online",
        "servico": "API Admissão apLIS",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/api/admissao/teste', methods=['GET'])
def teste_conexao():
    """
    Testa conexão com apLIS
    """
    try:
        response = requests.get(APLIS_URL, timeout=10)
        return jsonify({
            "conexao_ok": True,
            "status_code": response.status_code,
            "mensagem": "Conexão com apLIS estabelecida"
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
    Serve imagem do diretório temporário
    """
    try:
        arquivo_path = os.path.join(TEMP_IMAGES_DIR, filename)
        if os.path.exists(arquivo_path):
            # Detectar mimetype baseado na extensão
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
            return jsonify({"erro": "Imagem não encontrada"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


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
            return jsonify({"sucesso": 0, "erro": "Nome da imagem não fornecido"}), 400

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
        # 2. Se não existe local, tentar S3 via URL
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
            logger.error(f"[OCR] Imagem não encontrada: {imagem_nome}")
            return jsonify({
                "sucesso": 0,
                "erro": "Imagem não encontrada (nem arquivo local nem URL fornecida)"
            }), 404

        if not image_bytes:
            logger.error(f"[OCR] Falha ao carregar dados da imagem: {imagem_nome}")
            return jsonify({
                "sucesso": 0,
                "erro": "Falha ao carregar dados da imagem"
            }), 400

        # Criar modelo Gemini (usando 2.5 Flash - mais estável e com mais cota)
        model = GenerativeModel("gemini-2.5-flash")

        # Detectar mime type baseado na extensão
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

        # ⚡ APLICAR RATE LIMITING ANTES DE CHAMAR VERTEX AI
        logger.info("[OCR] ⏳ Verificando rate limit...")
        vertex_rate_limiter.wait_if_needed()
        logger.info("[OCR] ✅ Rate limit OK, prosseguindo com requisição")

        # Prompt para extrair dados com rastreabilidade
        prompt = f"""
Voce e um Especialista em OCR de Alta Precisao para Documentos Medicos e de Identificacao.

MISSAO: EXTRAIR DADOS COM MAXIMA PRECISAO - CADA CARACTERE IMPORTA!

======================================================================
ATENCAO ESPECIAL - EXTRACAO DE EXAMES DE LAUDOS MEDICOS
======================================================================

⚠️ CRITICO - APENAS EXAMES MARCADOS ⚠️

VOCE SO PODE INCLUIR EXAMES QUE ESTAO VISIVELMENTE MARCADOS!

O QUE SIGNIFICA "MARCADO":
- Um checkbox vazio (☐) NAO é marcado - IGNORE
- Um checkbox preenchido (☑) SIM é marcado - EXTRAIA
- Um circulo vazio (○) NAO é marcado - IGNORE
- Um circulo preenchido (●) SIM é marcado - EXTRAIA
- Um circulo com X (⊗) é marcado - EXTRAIA
- Sem nenhuma marca é NAO marcado - IGNORE

REGRA ABSOLUTA:
SE NAO HOUVER UMA MARCA VISIVEL AO LADO DO NOME, IGNORE COMPLETAMENTE!

EXEMPLO DE COMO O DOCUMENTO APARECE:
   ☑ Ectocervice        ← MARCADO - EXTRAIA "Ectocervice"
   ☐ Endocervice       ← NAO MARCADOS - IGNORE COMPLETAMENTE
   ☑ Fundo de Saco     ← MARCADO - EXTRAIA "Fundo de Saco"
   ☐ Vagina            ← NAO MARCADOS - IGNORE COMPLETAMENTE
   ☑ Citologia Convencional  ← MARCADO - EXTRAIA "Citologia Convencional"
   ☐ Histopatologia    ← NAO MARCADOS - IGNORE COMPLETAMENTE

RESULTADO CORRETO PARA O EXEMPLO ACIMA:
"itens_exame": ["Ectocervice", "Fundo de Saco", "Citologia Convencional"]

RESULTADO ERRADO (NAO FACA ISSO):
"itens_exame": ["Ectocervice", "Endocervice", "Fundo de Saco", "Vagina", "Citologia Convencional", "Histopatologia"]
↑ ERRADO - INCLUIU ITEMS NAO MARCADOS!

COMO PROCEDER:
1. Leia CADA LINHA da lista de opcoes
2. Identifique SE TEM UMA MARCA (☑, ●, ⊗, etc) ao lado
3. SE TEM MARCA → Extraia o nome do exame
4. SE NAO TEM MARCA → IGNORE COMPLETAMENTE
5. Sempre revise sua lista antes de retornar - tem certeza que TODOS estao marcados?

IMPORTANTE: itens_exame deve ser um array de APENAS strings marcadas!
Formato correto: "itens_exame": ["Ectocervice", "Fundo de Saco"]
Nunca inclua items que voce NAO VIU MARCADOS!

======================================================================


REGRAS DE EXTRACAO FUNDAMENTAIS


1. LEIA CARACTERE POR CARACTERE - Não adivinhe, não interprete, COPIE EXATAMENTE o que está escrito
2. NOMES COMPLETOS - Extraia o nome COMPLETO, não abrevie, não corte nenhuma parte
3. DATAS EXATAS - Copie a data exatamente como aparece e depois converta para YYYY-MM-DD
4. CPF/RG/DOCUMENTOS - Copie todos os dígitos visíveis, sem erros de transcrição
5. CONFIANÇA REALISTA - Se a imagem está ruim ou texto ilegível, reduza o score de confiança


TIPOS DE DOCUMENTOS E ONDE PROCURAR


 DOCUMENTO DE IDENTIDADE (RG, CNH, OAB, CRN, CRM, etc):

    CARTEIRA DA OAB - ATENÇÃO ESPECIAL:
   Esta é uma carteira de advogado da Ordem dos Advogados do Brasil.

   LOCALIZAÇÃO DOS CAMPOS NA CARTEIRA OAB:
   - NOME: Campo principal logo abaixo do brasão, geralmente após "NOME:" ou "FILIAÇÃO:"
     * Exemplo: "ANA PAULA CORREIA DE SOUZA" (extraia COMPLETO, sem cortar)

   - DATA DE NASCIMENTO: Procure por labels:
     * "DATA DE NASCIMENTO"
     * "NASCIMENTO"
     * "NATURALIDADE"
     * Formato comum: DD/MM/YYYY ou DD/MM/YY
     * Exemplo na OAB: "17/02/1985"

   - CPF: Procure ESPECIFICAMENTE por:
     * Label "CPF" seguido de números
     * Formato: XXX.XXX.XXX-XX ou apenas 11 dígitos
     * Exemplo: "013.374.042-88" → extrair como "01337404288"
     * IMPORTANTE: O CPF na OAB geralmente está na parte superior direita

   - RG: Pode aparecer como:
     * "RG", "IDENTIDADE", "REGISTRO GERAL"
     * Número seguido do órgão emissor (ex: "2.076.842 - SSP/DF")

   - INSCRIÇÃO OAB: Número de registro do advogado
     * Geralmente tem formato como "DF 13827"

   OUTROS DOCUMENTOS DE IDENTIDADE:
   - RG/CNH: Similar à OAB, procure pelos mesmos campos
   - CRM/CRN: Documentos de profissionais da saúde, mesma lógica

 CARTEIRA DE CONVÊNIO:
   - NOME PACIENTE: Campo principal de identificação
   - MATRÍCULA: "MATRÍCULA", "CARTEIRINHA", número principal
   - PLANO: Nome do convênio/operadora
   - VALIDADE: Data de validade do plano

 PEDIDO MÉDICO / REQUISIÇÃO:
   - NOME PACIENTE: Início do documento, campo "Paciente"
   - EXAME SOLICITADO: "Procedimento", "Exame", "Especificação da Amostra"
   - MÉDICO: Nome e CRM do solicitante
   - DATA COLETA: "Data da coleta", "Data"
   - DADOS CLÍNICOS: Campo "Dados Clínicos", "Informações Clínicas"

 LAUDO MÉDICO / RESULTADO DE EXAME:
   ATENÇÃO: Este documento contém MÚLTIPLAS DATAS - você deve identificar CORRETAMENTE qual é qual!

   CAMPOS OBRIGATÓRIOS:
   - NOME PACIENTE: Campo "Paciente" no topo do documento
     * Exemplo: "KAUA LARSSON LOPES DE SOUSA"

   - DATA DE NASCIMENTO: Procure por "Data Nascimento" ou similar
     * NO LAUDO, geralmente está no cabeçalho junto com dados do paciente
     * Formato: DD/MM/YYYY
     * Exemplo: "28/07/2006"
     * NÃO confunda com "Data de Emissão" ou "Data da Entrega"

   - DATA DA COLETA: Procure por "Data de coleta" ou "Data da recebimento"
     * É a data em que o material foi coletado do paciente
     * Formato: DD/MM/YYYY HH:MM:SS
     * Exemplo: "10/09/2025 11:46:00"
     * NÃO confunda com "Data de Nascimento"

   - ORDEM DE SERVIÇO: Número identificador do exame
     * Procure por "Ordem Serviço", "OS", "Número"
     * Exemplo: "35590420"

   - EXAMES REALIZADOS (MUITO IMPORTANTE!): Lista de exames/procedimentos
     * NO LAUDO MÉDICO, os exames estão na tabela de RESULTADOS
     * VOCÊ DEVE EXTRAIR TODOS OS NOMES DOS EXAMES da tabela de resultados
     * Procure na seção Exame, Resultado, ou na tabela de valores
     * Cada linha da tabela geralmente tem: Nome do Exame, Resultado, Unidade, Referência
     * EXTRAIA APENAS OS NOMES DOS EXAMES, ignore os valores numéricos
     * Exemplo: Se ver CREATININA 1.00 mg/dL, extraia apenas CREATININA
     * Exemplo: Se ver TSH 2.5 mIU/L, extraia apenas TSH
     * Adicione todos os nomes de exames no campo itens_exame como array

 FRASCO DE AMOSTRA:
   - CÓDIGO: Número ou código de barras principal
   - NOME PACIENTE: Se visível no rótulo
   - TIPO MATERIAL: Descrição do material coletado


 ATENÇÃO ESPECIAL PARA NOMES


CORRETO :
- "ANA PAULA CORREIA DE SOUZA" (todos os nomes intermediários incluídos)
- "JOSÉ CARLOS DA SILVA JÚNIOR" (inclui sufixos como JÚNIOR, NETO, FILHO)
- "MARIA DE LOURDES SANTOS" (inclui preposições DE, DA, DOS)

ERRADO :
- "ANA PAULA COVEIRA" (nome cortado ou com erro de OCR)
- "JOSE CARLOS SILVA" (faltando partes do nome)
- "ANA P. SOUZA" (abreviado incorretamente)


 ATENÇÃO ESPECIAL PARA DATA DE NASCIMENTO


 ISTO É CRÍTICO - DATA DE NASCIMENTO É OBRIGATÓRIA

A DATA DE NASCIMENTO é ESSENCIAL para cálculo de idade! Você DEVE encontrá-la!

⚠️ MÉTODO DUPLO DE EXTRAÇÃO ⚠️

MÉTODO 1 - DATA DE NASCIMENTO EXPLÍCITA (PREFERENCIAL):
ONDE PROCURAR:
1. Procure pelas palavras: "DATA DE NASCIMENTO", "NASCIMENTO", "NATURALIDADE"
2. Na carteira da OAB, geralmente está NA PARTE SUPERIOR do documento
3. Está sempre em formato de data: DD/MM/YYYY ou DD/MM/YY
4. Se encontrar a data, extraia e converta para YYYY-MM-DD

MÉTODO 2 - CALCULAR A PARTIR DA IDADE (SE NÃO ENCONTRAR DATA):
SE NÃO ENCONTRAR A DATA DE NASCIMENTO, procure pela IDADE DO PACIENTE:

ONDE PROCURAR A IDADE:
- Geralmente ao lado do nome do paciente
- Formato: "XX anos", "XX anos XX meses", "XX anos XX meses XX dias"
- Exemplos:
  * "48 anos"
  * "48 anos 10 meses"
  * "48 anos 10 meses 10 dias"
  * "Paciente: MARIA SILVA (35 anos 6 meses)"

COMO EXTRAIR A IDADE:
1. Identifique o padrão "XX anos" ou "XX anos XX meses XX dias"
2. Extraia APENAS os números (anos, meses, dias)
3. Coloque no campo "idade_formatada" como string
4. Exemplo: Se vir "48 anos 10 meses 10 dias" → extraia como "48 anos 10 meses 10 dias"
5. O sistema calculará automaticamente a data de nascimento a partir disso

FORMATO DE SAÍDA:
Se encontrou DATA: {{"valor": "1977-02-22", "fonte": "arquivo.jpg", "confianca": 0.95}}
Se encontrou IDADE: {{"valor": "48 anos 10 meses 10 dias", "fonte": "arquivo.jpg", "confianca": 0.90, "tipo": "idade_formatada"}}

⚠️ REGRA: Sempre tente PRIMEIRO a data de nascimento explícita. Use a idade APENAS se não encontrar a data!

⚠️ ATENÇÃO CRÍTICA - FORMATO BRASILEIRO DE DATA ⚠️

NO BRASIL, A DATA É SEMPRE: DIA/MÊS/ANO (DD/MM/YYYY)
NUNCA É: MÊS/DIA/ANO (formato americano)

FORMATOS QUE VOCÊ VAI ENCONTRAR NO DOCUMENTO:
- 01/01/1965 → PRIMEIRO NÚMERO É O DIA (01), SEGUNDO É O MÊS (01)
- 17/02/1985 → dia 17, mês 02 (fevereiro), ano 1985
- 28/07/2006 → dia 28, mês 07 (julho), ano 2006
- 17/02/85 (dia/mês/ano com 2 dígitos)
- 17.02.1985 (com pontos ao invés de barras)
- 17 FEV 1985 (com mês por extenso)
- 17-02-1985 (com traços)

COMO CONVERTER PARA YYYY-MM-DD:
1. Leia a data no formato brasileiro: DD/MM/YYYY
2. Identifique: PRIMEIRO número = DIA, SEGUNDO número = MÊS, TERCEIRO = ANO
3. Reorganize para: ANO-MÊS-DIA

EXEMPLOS PASSO A PASSO:

Documento mostra: "01/01/1965"
Passo 1: Identificar → DIA=01, MÊS=01, ANO=1965
Passo 2: Converter → "1965-01-01" ✅ CORRETO
NUNCA FAÇA: "1965-10-01" ❌ ERRADO! (inverteu dia e mês)

Documento mostra: "17/02/1985"
Passo 1: Identificar → DIA=17, MÊS=02, ANO=1985
Passo 2: Converter → "1985-02-17" ✅ CORRETO

Documento mostra: "28/07/2006"
Passo 1: Identificar → DIA=28, MÊS=07, ANO=2006
Passo 2: Converter → "2006-07-28" ✅ CORRETO

MAIS EXEMPLOS DE CONVERSÃO:
- "01/01/1965" → "1965-01-01" (NÃO "1965-10-01"!)
- "17/02/1985" → "1985-02-17" (dia 17, mês 02)
- "17/02/85" → "1985-02-17" (ano de 2 dígitos)
- "17.02.1985" → "1985-02-17" (pontos ao invés de barras)
- "17 FEV 1985" → "1985-02-17" (mês por extenso)
- "28/07/2006" → "2006-07-28" (dia 28, mês 07)


 EXEMPLO PRÁTICO - LAUDO MÉDICO COM MÚLTIPLAS DATAS


Imagine que você está lendo este trecho de um laudo:

EXEMPLO DO LAUDO:
-------------------------------------------------------
Paciente: KAUA LARSSON LOPES DE SOUSA
Data Nascimento: 28/07/2006        Ordem Servico: 35590420
Instituicao: LAB                    Data de Emissao: 17/09/2025 07:29:37

Exame: CREATININA
Data de coleta: 10/09/2025 11:46:00
Data de recebimento: 10/09/2025 17:16:57

Resultado:
Creatinina: 1.00 mg/dL
-------------------------------------------------------

EXTRAÇÃO CORRETA:
- data_nascimento: 2006-07-28  (é a data ao lado de Data Nascimento)
- dtaColeta: 2025-09-10  (é a Data de coleta, NÃO a Data de Emissão)
- ordem_servico: 35590420
- nome: KAUA LARSSON LOPES DE SOUSA

EXTRAÇÃO ERRADA (NÃO FAÇA ISSO!):
- data_nascimento: 2025-09-17  (ERRADO - confundiu com Data de Emissão)
- dtaColeta: 2025-09-19  (ERRADO - pegou data errada)

FORMATO DE SAÍDA (sempre YYYY-MM-DD):
{{"valor": "1985-02-17", "fonte": "arquivo.jpg", "confianca": 0.95}}

VALIDAÇÃO OBRIGATÓRIA:
- Formato deve ser YYYY-MM-DD
- Mês deve estar entre 01 e 12
- Dia deve estar entre 01 e 31
- Se não encontrar a data, use null mas com confianca 0.0


 ATENÇÃO ESPECIAL PARA CPF


 ISTO É CRÍTICO - LEIA ATENTAMENTE 

O CPF É UM DOS CAMPOS MAIS IMPORTANTES! Você DEVE encontrá-lo!

ONDE PROCURAR O CPF:
1. Procure pela palavra "CPF" em MAIÚSCULAS no documento
2. O CPF está SEMPRE próximo dessa palavra
3. Na carteira da OAB, geralmente está NO LADO DIREITO SUPERIOR
4. É uma sequência de 11 dígitos, pode estar formatada ou não

FORMATOS QUE VOCÊ VAI ENCONTRAR:
- 013.374.042-88 (com pontos e traço)
- 013 374 042 88 (com espaços)
- 01337404288 (sem formatação)

COMO EXTRAIR:
1. Identifique o texto "CPF" no documento
2. Pegue os números que vêm LOGO APÓS ou ABAIXO
3. Remova TODOS os pontos, traços e espaços
4. Retorne APENAS os 11 dígitos

EXEMPLO REAL:
- Documento mostra: "CPF: 013.374.042-88"
- Você deve extrair: "01337404288"

FORMATO DE SAÍDA (sempre sem formatação):
{{"valor": "01337404288", "fonte": "arquivo.jpg", "confianca": 0.95}}

VALIDAÇÃO OBRIGATÓRIA:
- CPF deve ter EXATAMENTE 11 dígitos numéricos
- Se tiver menos ou mais, você errou na extração
- Se não encontrar o CPF, use null mas com confianca 0.0


 FORMATO JSON DE SAÍDA


{{
    "paciente": {{
        "NomPaciente": {{"valor": "NOME COMPLETO EM MAIÚSCULAS", "fonte": "{imagem_nome}", "confianca": 0.95}},
        "DtaNasc": {{"valor": "YYYY-MM-DD", "fonte": "{imagem_nome}", "confianca": 0.90}},
        "NumCPF": {{"valor": "apenas números 11 dígitos", "fonte": "{imagem_nome}", "confianca": 0.95}},
        "NumRG": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "TelCelular": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.80}},
        "DscEndereco": {{"valor": "string endereço completo", "fonte": "{imagem_nome}", "confianca": 0.75}}
    }},
    "medico": {{
        "NomMedico": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.90}},
        "numConselho": {{"valor": "string CRM", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "ufConselho": {{"valor": "UF", "fonte": "{imagem_nome}", "confianca": 0.90}}
    }},
    "convenio": {{
        "nome_fonte_pagadora": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "matConvenio": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "numGuia": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.90}}
    }},
    "requisicao": {{
        "dtaColeta": {{"valor": "YYYY-MM-DD", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "dadosClinicos": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.80}},
        "itens_exame": [
            {{
                "descricao_ocr": "NOME DO EXAME",
                "setor_sugerido": "laboratório ou anátomo patológico"
            }}
        ]
    }},
    "tipo_documento": "documento_identidade ou pedido_medico ou carteira_convenio ou frasco",
    "comentarios_gerais": {{
        "observacoes": "qualquer informação adicional relevante",
        "requisicao_entrada": "código se encontrado",
        "codigos_barras": ["array com TODOS os códigos de barras/requisições encontrados na imagem", "ex: 0085075447003", "ex: 0200051653008"]
    }}
}}


 CÓDIGOS DE BARRAS / REQUISIÇÕES MÚLTIPLAS


IMPORTANTE: Muitas imagens de pedido têm DOIS códigos de barras:
- Um começando com 0085 (requisição tipo 1)
- Outro começando com 0200 (requisição tipo 2)

VOCÊ DEVE EXTRAIR TODOS OS CÓDIGOS QUE ENCONTRAR!

FORMATO:
- Códigos geralmente começam com 0085, 0200, 004, 008, etc.
- São sequências numéricas longas (10-15 dígitos)
- Aparecem abaixo ou ao lado de códigos de barras na imagem

EXEMPLOS:
- "0085075447003" e "0200075447003" (mesma base, prefixos diferentes)
- "0040000356004"
- "0200051653008" e "0085051653008"

EXTRAÇÃO:
1. Procure por códigos de barras na imagem
2. Extraia TODOS os códigos numéricos longos que encontrar
3. Adicione ao array "codigos_barras" em comentarios_gerais
4. O primeiro código encontrado também vai em "requisicao_entrada" (retrocompatibilidade)

EXEMPLO DE SAÍDA:
{{
    "comentarios_gerais": {{
        "requisicao_entrada": "0200051653008",
        "codigos_barras": ["0200051653008", "0085051653008"]
    }}
}}


 INSTRUÇÕES FINAIS


1. Se não conseguir ler um campo, use null no "valor" mas mantenha "fonte" e "confianca"
2. Score de confianca: 1.0 = perfeito, 0.5 = duvidoso, 0.0 = não encontrado
3. Retorne APENAS JSON válido, SEM markdown, SEM comentários, SEM ```json
4. Em caso de dúvida entre interpretações, escolha a mais literal (o que está escrito)
5. NUNCA invente dados - se não vê claramente, melhor deixar null

ANALISE A IMAGEM AGORA E EXTRAIA OS DADOS COM MÁXIMA PRECISÃO!
"""

        # Gerar resposta com retry em caso de rate limit
        logger.info("[OCR] Enviando para Vertex AI...")
        max_retries = 3
        retry_delay = 15  # Começar com 15 segundos

        for attempt in range(max_retries):
            try:
                response = model.generate_content([prompt, image_part])
                texto_resposta = response.text.strip()
                logger.info(f"[OCR] ✅ Resposta recebida do Vertex AI: {len(texto_resposta)} caracteres")
                logger.debug(f"[OCR] Primeiros 500 chars: {texto_resposta[:500]}...")
                break  # Sucesso, sair do loop
            except Exception as e:
                error_str = str(e)
                logger.error(f"[OCR] Erro na tentativa {attempt + 1}/{max_retries}: {error_str}")

                # Se for erro 429 (rate limit) e ainda tem tentativas, aguardar
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 15s, 30s, 60s
                    logger.warning(f"[OCR] ⏳ Rate limit 429 detectado. Aguardando {wait_time}s antes de tentar novamente...")
                    time.sleep(wait_time)
                    continue

                # Se não é 429 ou é a última tentativa, retornar erro
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

        # Limpar possíveis markdown do JSON
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

            # 🆕 VALIDAÇÃO E CORREÇÃO AUTOMÁTICA DE DATAS
            def validar_e_corrigir_data(data_str, campo_nome="data"):
                """
                Valida e corrige datas no formato YYYY-MM-DD
                Detecta se dia/mês foram invertidos e corrige automaticamente
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

                    # Validação básica
                    if mes_int < 1 or mes_int > 12:
                        # Mês inválido! Provavelmente inverteu com dia
                        if dia_int >= 1 and dia_int <= 12:
                            # Dia está na faixa de mês válido, provavelmente inverteu
                            print(f"[OCR] ⚠️ CORREÇÃO AUTOMÁTICA: {campo_nome}")
                            print(f"[OCR]   Data INCORRETA: {data_str} (mês={mes_int} inválido)")
                            print(f"[OCR]   Invertendo dia ↔ mês...")
                            data_corrigida = f"{ano}-{dia:02d}-{mes:02d}"
                            print(f"[OCR]   Data CORRIGIDA: {data_corrigida}")
                            return data_corrigida

                    # Se dia é inválido para o mês, também pode ser inversão
                    if dia_int > 31 or dia_int < 1:
                        print(f"[OCR] ⚠️ Data com dia inválido: {data_str} (dia={dia_int})")

                    return data_str

                except (ValueError, IndexError) as e:
                    print(f"[OCR] ⚠️ Erro ao validar data {data_str}: {e}")
                    return data_str

            # Aplicar validação nas datas do paciente
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
                            "confianca": 0.85  # Confiança um pouco menor pois é calculado
                        }
                        print(f"[OCR] ✅ Data de nascimento corrigida: {data_corrigida}")

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
                print(f"[OCR]  DADOS DO PACIENTE EXTRAÍDOS ")
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

                # Endereço
                end = paciente.get('DscEndereco', {}).get('valor') if isinstance(paciente.get('DscEndereco'), dict) else paciente.get('DscEndereco')
                print(f"[OCR]    Endereço: {end}")

                print(f"[OCR] ")
            else:
                print(f"[OCR]  ATENÇÃO: Nenhum dado de paciente encontrado no JSON!")

        except json.JSONDecodeError as e:
            print(f"[OCR]  Erro ao fazer parse do JSON: {e}")
            print(f"[OCR] Texto recebido: {texto_resposta}")
            return jsonify({
                "sucesso": 0,
                "erro": "Erro ao processar resposta do OCR",
                "detalhes": texto_resposta
            }), 500

        #  FALLBACK CRÍTICO: Se for pedido médico e não tiver exames, forçar extração
        tipo_doc = dados_extraidos.get('tipo_documento', '')
        if tipo_doc == 'pedido_medico':
            if 'requisicao' not in dados_extraidos:
                dados_extraidos['requisicao'] = {}
            if 'itens_exame' not in dados_extraidos['requisicao'] or not dados_extraidos['requisicao']['itens_exame']:
                print(f"[OCR]  FALLBACK: Pedido médico sem exames detectado! Forçando extração...")
                # Tentar extrair exame dos dados clínicos ou usar genérico
                dados_clinicos_texto = dados_extraidos.get('requisicao', {}).get('dadosClinicos', {}).get('valor', '')

                # Lista de palavras-chave para identificar tipo de exame
                exame_fallback = "EXAME HISTOPATOLÓGICO"  # Padrão genérico

                if dados_clinicos_texto:
                    texto_upper = dados_clinicos_texto.upper()
                    if any(keyword in texto_upper for keyword in ['BIOPSIA', 'BIÓPSIA', 'HISTOPATOLOG', 'LESAO', 'LESÃO']):
                        exame_fallback = "HISTOPATOLÓGICO"
                    elif any(keyword in texto_upper for keyword in ['HEMOGRAMA', 'GLICEMIA', 'UREIA', 'CREATININA']):
                        exame_fallback = "MEDICINA LABORATORIAL"
                    elif any(keyword in texto_upper for keyword in ['CITOLOGIA', 'PAPANICO']):
                        exame_fallback = "COLPOCITOLOGIA"
                    elif any(keyword in texto_upper for keyword in ['PCR', 'COVID']):
                        exame_fallback = "PCR"

                dados_extraidos['requisicao']['itens_exame'] = [{
                    "descricao_ocr": exame_fallback,
                    "setor_sugerido": "anátomo patológico",
                    "fonte_extracao": "fallback_automatico"
                }]
                print(f"[OCR]  FALLBACK aplicado: Exame '{exame_fallback}' adicionado automaticamente")

        # CORREÇÃO AUTOMÁTICA DE PORTUGUÊS
        print(f"[OCR] Aplicando correção automática de português...")

        # Corrigir dados clínicos
        if 'requisicao' in dados_extraidos and isinstance(dados_extraidos['requisicao'], dict):
            if 'dadosClinicos' in dados_extraidos['requisicao'] and isinstance(dados_extraidos['requisicao']['dadosClinicos'], dict):
                texto_original = dados_extraidos['requisicao']['dadosClinicos'].get('valor', '')
                if texto_original and isinstance(texto_original, str):
                    texto_corrigido = corrigir_portugues(texto_original)
                    dados_extraidos['requisicao']['dadosClinicos']['valor'] = texto_corrigido
                    print(f"[OCR]  Dados clínicos corrigidos: {texto_corrigido[:50]}...")

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
                            exame['descricao_original'] = texto_original  # Manter original para referência
                            print(f"[OCR]  Exame {idx+1} corrigido: '{texto_corrigido}'")
                print(f"[OCR]  Todos os exames foram corrigidos")
            else:
                print(f"[OCR]  AVISO: Nenhum exame encontrado no campo itens_exame!")

        # NÃO remover campos null - retornar tudo que o Gemini extraiu
        print(f"[OCR] Retornando {len(dados_extraidos)} campos extraídos")

        # DEBUG: Mostrar se tem itens_exame
        if 'requisicao' in dados_extraidos and isinstance(dados_extraidos['requisicao'], dict):
            if 'itens_exame' in dados_extraidos['requisicao']:
                print(f"[OCR] ✓ itens_exame encontrado: {dados_extraidos['requisicao']['itens_exame']}")
            else:
                print(f"[OCR] ⚠ itens_exame NÃO encontrado na requisicao!")
                print(f"[OCR] Campos disponíveis em requisicao: {list(dados_extraidos['requisicao'].keys())}")

        # Log completo da resposta do Gemini para debug
        print(f"[OCR] === RESPOSTA COMPLETA DO GEMINI (primeiros 2000 chars) ===")
        print(texto_resposta[:2000])
        print(f"[OCR] ======================================================")

        return jsonify({
            "sucesso": 1,
            "mensagem": "OCR processado com sucesso (português corrigido)",
            "dados": dados_extraidos,
            "debug_resposta_gemini": texto_resposta[:10000]  # Aumentado para 1000 chars
        }), 200

    except Exception as e:
        logger.error(f"[OCR] ✗ Erro ao processar OCR: {str(e)}")
        logger.exception(f"[OCR] Stack trace:")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao processar OCR: {str(e)}"
        }), 500


def corrigir_portugues(texto):
    """
    Corrige erros de português usando Vertex AI
    """
    if not texto or len(texto.strip()) < 3:
        return texto

    try:
        model = GenerativeModel("gemini-2.5-flash")

        prompt = f"""Corrija APENAS os erros de ortografia e gramática no texto abaixo.
Mantenha o significado original.
Retorne SOMENTE o texto corrigido, sem explicações.

Texto: {texto}

Texto corrigido:"""

        response = model.generate_content(prompt)
        texto_corrigido = response.text.strip()

        print(f"[CORREÇÃO] Original: {texto}")
        print(f"[CORREÇÃO] Corrigido: {texto_corrigido}")

        return texto_corrigido
    except Exception as e:
        print(f"[CORREÇÃO] Erro ao corrigir: {e}")
        return texto  # Retorna original se falhar


# ============================================
# MAPEAMENTO COMPLETO DE TODOS OS EXAMES
# ============================================
MAPEAMENTO_EXAMES = {
    # MEDICINA LABORATORIAL - ID: 49
    'MEDICINA LABORATORIAL': 49,

    # CITOPATOLOGIA
    'BACTERIOSCOPIA': 50,
    'COLPOCITOLOGIA ONCÓTICA CONVENCIONAL': 20,
    'COLPOCITOLOGIA ONCÓTICA EM MEIO LÍQUIDO': 24,
    'CITOLOGIA HORMONAL ISOLADA': 21,
    'CITOLOGIA ONCÓTICA DE LÍQUIDOS': 4,
    'CITOLOGIA ANAL CONVENCIONAL': 33,
    'CITOLOGIA ANAL EM MEIO LIQUIDO': 34,
    'CITOLOGIA EM MEIO LÍQUIDO URINÁRIO': 35,
    'PROCEDIMENTO DIAGNÓSTICO LÂMINA DE PAAF ATÉ 5': 36,
    'PUNÇÃO BIOPSIA ASPIRATIVA': 17,

    # ANÁTOMO PATOLÓGICO
    'BIÓPSIA SOE': 1,
    'BIOPSIA SOE': 1,
    'BIÓPSIA': 1,  # Genérico = SOE
    'BIÓPSIA': 1,  # Genérico = SOE
    'HISTOPATOLOGIA': 1,  # Biópsia genérica
    'HISTOPATOLÓGICO': 1,
    'HISTOPATOLOGICO': 1,

    'PEÇA CIRÚRGICA SIMPLES': 2,
    'PECA CIRURGICA SIMPLES': 2,
    'PEÇA CIRÚRGICA COMPLEXA': 14,
    'PECA CIRURGICA COMPLEXA': 14,

    'BIÓPSIA SIMPLES': 23,
    'BIOPSIA SIMPLES': 23,
    'BIÓPSIA GÁSTRICA': 38,
    'BIOPSIA GASTRICA': 38,
    'BIÓPSIA DE MÚLTIPLOS FRAGMENTOS': 40,
    'BIOPSIA DE MULTIPLOS FRAGMENTOS': 40,

    'NECRÓPSIA DE FETO': 43,
    'NECROPSIA DE FETO': 43,
    'EXAME PER-OPERATÓRIO POR CONGELAÇÃO': 3,

    # VARIAÇÕES COMUNS DE BIÓPSIAS
    'LESAO DE PELE': 23,  # Biópsia simples
    'LESÃO DE PELE': 23,
    'LESAO': 23,
    'LESÃO': 23,
    'PELE': 23,
    'ABDOME': 23,
    'NODULO': 23,
    'NÓDULO': 23,
    'MAMA': 23,
    'TIREOIDE': 23,
    'TIROIDE': 23,

    # PCR
    'PCR': 51,
    'PCR EM TEMPO REAL DE HPV BAIXO/ALTO RISCO': 52,

    # REVISÃO
    'REVISÃO DE LÂMINA INTERNA': 10,
    'REVISAO DE LAMINA INTERNA': 10,
    'REVISÃO DE LÂMINA EXTERNO (BLOCO)': 11,
    'REVISAO DE LAMINA EXTERNO (BLOCO)': 11,
    'REVISÃO DE LÂMINA EXTERNO (BLOCO + LÂMINA)': 15,
    'REVISAO DE LAMINA EXTERNO (BLOCO + LAMINA)': 15,
    'REVISÃO DE LÂMINA INTERNA - CITOLOGIA': 39,
    'REVISAO DE LAMINA INTERNA - CITOLOGIA': 39,

    # IMUNOISTOQUÍMICA
    'IMUNOISTOQUÍMICA INTERNA': 6,
    'IMUNOISTOQUIMICA INTERNA': 6,
    'IMUNOISTOQUÍMICA EXTERNA (BLOCO)': 12,
    'IMUNOISTOQUIMICA EXTERNA (BLOCO)': 12,
    'IMUNOISTOQUÍMICA EXTERNA (BLOCO+LÂMINA)': 13,
    'IMUNOISTOQUIMICA EXTERNA (BLOCO+LAMINA)': 13,

    # EXAMES REALIZADOS POR PARCEIROS
    'CAPTURA HÍBRIDA': 22,
    'CAPTURA HIBRIDA': 22,

    # REDE APLIS
    'REDE - HISTOTÉCNICA': 26,
    'REDE - HISTOTECNICA': 26,
    'REDE - MACROSCOPIA': 27,
    'REDE - MICROSCOPIA': 25,
    'REDE - IHQ': 28,
    'REDE - CITOPATOLOGIA': 30,
    'REDE - HIBRIDIZAÇÃO IN SITU': 31,
    'REDE - HIBRIDIZACAO IN SITU': 31,
    'REDE - PAT. CLINICA': 29,
    'REDE - IHQ + TECNICA': 41,
    'REDE - IHQ + TECNICA + MICRO': 42,

    # INTEGRAÇÃO
    'INTEGRAÇÃO': 18,
    'INTEGRACAO': 18,

    # FATURAMENTO EXTERNO
    'FAT. EXT. CAPTURA': 32,
    'FAT. EXT. CITO.': 46,
    'FAT. EXT. CONV.': 37,
    'FAT. EXT. CONV. + HORMONAL': 45,
    'FAT. EXT. PAINEL': 19,
    'SULA - FAT - EXAME LIBERADO NA REQUISIÇÃO DE CAPTURA HÍBRIDA': 47,
}


def identificar_tipo_exame_backend(nome):
    """
    Identifica o tipo de exame e retorna o ID correto baseado na lista completa de exames
    1. Tenta match exato no dicionário
    2. Tenta match parcial (contém)
    3. Usa categorização por palavras-chave para exames laboratoriais
    Retorna: (tipo_exame, cod_exame)
    """
    nome_upper = nome.upper().strip()

    # 1. TENTAR MATCH EXATO NO DICIONÁRIO
    if nome_upper in MAPEAMENTO_EXAMES:
        cod = MAPEAMENTO_EXAMES[nome_upper]
        return 'MATCH_EXATO', cod

    # 2. TENTAR MATCH PARCIAL (contém)
    for exame_nome, cod in MAPEAMENTO_EXAMES.items():
        # Se o nome do exame contém a palavra-chave OU vice-versa
        if exame_nome in nome_upper or nome_upper in exame_nome:
            return 'MATCH_PARCIAL', cod

    # 3. CATEGORIZAÇÃO POR PALAVRAS-CHAVE PARA MEDICINA LABORATORIAL
    medicina_lab_keywords = [
        'CREATININA', 'FERRITINA', 'FERRO', 'SÉRICO', 'SERICO',
        'GAMA', 'GLUTAMIL', 'TRANSFERASE', 'GGT',
        'HEMOGLOBINA', 'GLICADA', 'HBA1C',
        'HEMOGRAMA', 'LEUCOGRAMA', 'PLAQUETAS', 'ERITROGRAMA',
        'LIPÍDICO', 'LIPIDICO', 'PERFIL', 'COLESTEROL', 'TRIGLICÉRIDES', 'TRIGLICERIDES', 'HDL', 'LDL', 'VLDL',
        'TESTOSTERONA', 'BIODISPONÍVEL', 'BIODISPONIVEL', 'LIVRE', 'TOTAL',
        'TSH', 'TIREOTRÓFICO', 'TIREOTROPICO', 'TIREOESTIMULANTE', 'ULTRASSENSÍVEL', 'ULTRASSENSIVEL',
        'TIROXINA', 'T4', 'T3', 'TRIIODOTIRONINA',
        'TRANSAMINASE', 'OXALACÉTICA', 'OXALACETICA', 'TGO', 'ASPARTATO', 'AMINO', 'AST',
        'PIRÚVICA', 'PIRUVICA', 'TGP', 'ALANINA', 'ALT',
        'UREIA', 'UREICO', 'BUN',
        'VITAMINA', 'B12', 'COBALAMINA', 'D', 'HIDROXI', '25-HIDROXI', 'CALCIFEROL',
        'GLICOSE', 'GLICEMIA', 'JEJUM', 'PÓS', 'POS', 'PRANDIAL',
        'ÁCIDO', 'ACIDO', 'ÚRICO', 'URICO',
        'CÁLCIO', 'CALCIO', 'IONICO', 'TOTAL',
        'FÓSFORO', 'FOSFORO', 'FOSFATO',
        'MAGNÉSIO', 'MAGNESIO',
        'SÓDIO', 'SODIO', 'NA',
        'POTÁSSIO', 'POTASSIO', 'K',
        'CLORO', 'CL',
        'PROTEÍNA', 'PROTEINA',
        'ALBUMINA', 'SÉRICA', 'SERICA',
        'GLOBULINA',
        'BILIRRUBINA', 'DIRETA', 'INDIRETA',
        'AMILASE', 'PANCREÁTICA', 'PANCREATICA',
        'LIPASE',
        'FOSFATASE', 'ALCALINA', 'FA',
        'DESIDROGENASE', 'LÁTICA', 'LATICA', 'LDH',
        'CPK', 'CREATINOQUINASE', 'MB', 'CK',
        'TROPONINA',
        'HORMÔNIO', 'HORMONIO',
        'ELETROFORESE', 'PROTEINOGRAMA',
        'PARATORMÔNIO', 'PARATORMONIO', 'PTH',
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
        'VHS', 'VELOCIDADE', 'HEMOSSEDIMENTAÇÃO', 'HEMOSSEDIMENTACAO',
        'PCR', 'PROTEINA', 'C', 'REATIVA',
        'FATOR', 'REUMATOIDE',
        'ANTI', 'ANTICORPO'
    ]

    # 4. FALLBACK: Categorização por tipo de exame

    # BIÓPSIAS / HISTOPATOLOGIA (palavras-chave genéricas) → BIÓPSIA SOE (ID: 1)
    biopsia_keywords = ['BIOPSIA', 'BIÓPSIA', 'HISTOPATOLOGIA', 'HISTOPATOLÓGICO',
                        'HISTOPATOLOGICO', 'LESAO', 'LESÃO', 'NODULO', 'NÓDULO']
    if any(keyword in nome_upper for keyword in biopsia_keywords):
        return 'ANÁTOMO PATOLÓGICO', 1

    # CITOPATOLOGIA (palavras-chave genéricas) → Depende do tipo específico
    cito_keywords = ['CITOLOGIA', 'CITOPATOLOGIA', 'COLPOCITOLOGIA', 'PAPANICOLAU',
                     'PREVENTIVO', 'ONCÓTICA', 'ONCOTICA']
    if any(keyword in nome_upper for keyword in cito_keywords):
        # Se tem "LIQUIDO" ou "LÍQUIDO", é meio líquido (ID: 24)
        if 'LIQUIDO' in nome_upper or 'LÍQUIDO' in nome_upper:
            return 'CITOPATOLOGIA', 24
        # Senão é convencional (ID: 20)
        return 'CITOPATOLOGIA', 20

    # MEDICINA LABORATORIAL (exames de sangue)
    if any(keyword in nome_upper for keyword in medicina_lab_keywords):
        return 'MEDICINA LABORATORIAL', 49

    # Não identificado
    return 'DESCONHECIDO', None


def buscar_dados_requisicao_simples(cod_requisicao):
    """
    Busca dados básicos de uma requisição do apLIS (versão simplificada para consolidação)

    Args:
        cod_requisicao: Código da requisição

    Returns:
        dict com dados básicos ou None se não encontrar
    """
    try:
        logger.info(f"[BUSCA_SIMPLES] Buscando requisição {cod_requisicao} do apLIS...")

        # Buscar nos últimos 365 dias
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

        # Procurar requisição específica
        for req in lista:
            if req.get("CodRequisicao") == cod_requisicao:
                logger.info(f"[BUSCA_SIMPLES] ✅ Requisição encontrada: {cod_requisicao}")

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

        logger.warning(f"[BUSCA_SIMPLES] ⚠️ Requisição {cod_requisicao} não encontrada")
        return None

    except Exception as e:
        logger.error(f"[BUSCA_SIMPLES] Erro ao buscar requisição: {e}")
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

        print(f"[CONSOLIDAR] Consolidando {len(resultados_ocr)} resultados OCR para requisição {cod_requisicao}")
        print(f"[CONSOLIDAR] Dados da API recebidos: {bool(dados_api)}")

        # 🆕 BUSCAR REQUISIÇÕES MÚLTIPLAS AUTOMATICAMENTE (0085 e 0200)
        codigos_encontrados = set()

        # Coletar TODOS os códigos de barras do OCR
        for resultado in resultados_ocr:
            dados_ocr = resultado.get('dados', {})
            comentarios = dados_ocr.get('comentarios_gerais', {})

            # Código único (retrocompatibilidade)
            if comentarios.get('requisicao_entrada'):
                codigos_encontrados.add(comentarios['requisicao_entrada'])

            # Múltiplos códigos (novo formato)
            if isinstance(comentarios.get('codigos_barras'), list):
                for codigo in comentarios['codigos_barras']:
                    if codigo and isinstance(codigo, str):
                        codigos_encontrados.add(codigo.strip())

        print(f"[CONSOLIDAR] 📊 Códigos de barras encontrados no OCR: {codigos_encontrados}")

        # Se encontrou múltiplos códigos E não tem dados_api ainda, buscar todos
        if len(codigos_encontrados) > 1 and not dados_api:
            print(f"[CONSOLIDAR] 🔍 Buscando automaticamente {len(codigos_encontrados)} requisições...")

            requisicoes_buscadas = {}
            for codigo in codigos_encontrados:
                print(f"[CONSOLIDAR] 📞 Buscando requisição: {codigo}")
                try:
                    # Buscar direto do apLIS usando a função existente
                    # NOTA: Esta é uma busca simples - a função completa buscar_requisicao_integrada
                    # será chamada pelo frontend depois
                    dados_req = buscar_dados_requisicao_simples(codigo)

                    if dados_req and dados_req.get('paciente'):
                        requisicoes_buscadas[codigo] = dados_req
                        print(f"[CONSOLIDAR] ✅ Requisição {codigo} encontrada!")
                    else:
                        print(f"[CONSOLIDAR] ⚠️ Requisição {codigo} não encontrada ou sem dados de paciente")

                except Exception as e:
                    print(f"[CONSOLIDAR] ❌ Erro ao buscar requisição {codigo}: {e}")
                    import traceback
                    print(f"[CONSOLIDAR] Traceback: {traceback.format_exc()}")

            # Escolher a requisição com MAIS dados do paciente
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
                    print(f"[CONSOLIDAR] 📈 Score de {codigo}: {score} campos preenchidos")

                    if score > melhor_score:
                        melhor_score = score
                        melhor_codigo = codigo

                if melhor_codigo:
                    dados_api = requisicoes_buscadas[melhor_codigo]
                    cod_requisicao = melhor_codigo
                    print(f"[CONSOLIDAR] 🏆 Usando requisição {melhor_codigo} (mais completa: {melhor_score} campos)")
                    print(f"[CONSOLIDAR] 📋 Paciente: {dados_api.get('paciente', {}).get('nome')}")
            else:
                print(f"[CONSOLIDAR] ⚠️ Nenhuma requisição encontrada no apLIS")

        # Estrutura do JSON consolidado
        resultado_consolidado = {
            "metadata": {
                "timestamp_processamento": datetime.now().isoformat(),
                "total_requisicoes": 1,
                "versao_sistema": "2.0 - Sistema de Admissão com OCR"
            },
            "requisicoes": [{
                "comentarios_gerais": {
                    "alertas_processamento": "Processamento automático via OCR",
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

            # Mesclar dados do paciente - 🆕 MESCLAGEM INTELIGENTE (não sobrescrever valores bons com null)
            if 'paciente' in dados_ocr and isinstance(dados_ocr['paciente'], dict):
                for key, value in dados_ocr['paciente'].items():
                    campo_atual = resultado_consolidado["requisicoes"][0]["paciente"].get(key)

                    # Extrair valores e confiança do novo dado
                    if isinstance(value, dict):
                        novo_valor = value.get('valor')
                        nova_confianca = value.get('confianca', 0)
                    else:
                        novo_valor = value
                        nova_confianca = 0

                    # Decidir se adiciona/sobrescreve
                    if campo_atual is None:
                        # Campo não existe, adicionar
                        resultado_consolidado["requisicoes"][0]["paciente"][key] = value
                    elif isinstance(campo_atual, dict):
                        valor_atual = campo_atual.get('valor')
                        confianca_atual = campo_atual.get('confianca', 0)

                        # Só sobrescrever se o novo valor for melhor
                        if (valor_atual is None or valor_atual == '' or valor_atual == 'null') and novo_valor:
                            resultado_consolidado["requisicoes"][0]["paciente"][key] = value
                        elif nova_confianca > confianca_atual and novo_valor:
                            resultado_consolidado["requisicoes"][0]["paciente"][key] = value
                    else:
                        resultado_consolidado["requisicoes"][0]["paciente"][key] = value

                # 🆕 PÓS-PROCESSAMENTO: Verificar se DtaNascimento ou idade_formatada contém idade
                # e calcular a data de nascimento
                pac_consolidado = resultado_consolidado["requisicoes"][0]["paciente"]

                # Verificar campo DtaNascimento
                if 'DtaNascimento' in pac_consolidado:
                    dta_obj = pac_consolidado['DtaNascimento']
                    if isinstance(dta_obj, dict):
                        dta_valor = dta_obj.get('valor')
                        # Se contém "anos", é idade formatada
                        if dta_valor and isinstance(dta_valor, str) and 'anos' in dta_valor.lower():
                            print(f"[CONSOLIDAR] 🎂 OCR extraiu idade no campo DtaNascimento: {dta_valor}")
                            data_calculada = calcular_data_nascimento_por_idade(dta_valor)
                            if data_calculada:
                                pac_consolidado['DtaNascimento'] = {
                                    "valor": data_calculada,
                                    "fonte": f"Calculado de idade: {dta_valor}",
                                    "confianca": 0.85
                                }
                                print(f"[CONSOLIDAR] ✅ Data calculada: {data_calculada}")

                # Verificar campo idade_formatada (alternativo)
                if 'idade_formatada' in pac_consolidado:
                    idade_obj = pac_consolidado['idade_formatada']
                    if isinstance(idade_obj, dict):
                        idade_valor = idade_obj.get('valor')
                        if idade_valor and isinstance(idade_valor, str):
                            print(f"[CONSOLIDAR] 🎂 OCR extraiu campo idade_formatada: {idade_valor}")
                            data_calculada = calcular_data_nascimento_por_idade(idade_valor)
                            if data_calculada:
                                # Criar ou atualizar DtaNascimento
                                pac_consolidado['DtaNascimento'] = {
                                    "valor": data_calculada,
                                    "fonte": f"Calculado de idade: {idade_valor}",
                                    "confianca": 0.85
                                }
                                print(f"[CONSOLIDAR] ✅ Data calculada de idade_formatada: {data_calculada}")
                                # Remover campo idade_formatada após processamento
                                del pac_consolidado['idade_formatada']

            # Mesclar dados do médico - 🆕 MESCLAGEM INTELIGENTE
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

            # Mesclar dados do convênio - 🆕 MESCLAGEM INTELIGENTE
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

            # Mesclar dados da requisição - INCLUIR TODOS OS CAMPOS (dict, list, str, etc)
            if 'requisicao' in dados_ocr and isinstance(dados_ocr['requisicao'], dict):
                tipo_doc = dados_ocr.get('tipo_documento', '')
                print(f"[CONSOLIDAR] 📋 Processando requisição da imagem: {imagem_nome}")
                print(f"[CONSOLIDAR] 📋 Tipo de documento: {tipo_doc}")
                print(f"[CONSOLIDAR] 📋 Campos em requisição: {list(dados_ocr['requisicao'].keys())}")

                for key, value in dados_ocr['requisicao'].items():
                    print(f"[CONSOLIDAR]   Processando campo: {key}, tipo: {type(value)}")

                    # Para itens_exame, adicionar de pedido_medico OU laudo_medico
                    if key == 'itens_exame' and isinstance(value, list):
                        print(f"[CONSOLIDAR]   🔬 Campo itens_exame encontrado! Tipo doc: {tipo_doc}, Qtd exames: {len(value)}")

                        # Adicionar exames de documentos tipo "pedido_medico" ou "laudo_medico"
                        if tipo_doc in ['pedido_medico', 'laudo_medico'] and len(value) > 0:
                            print(f"[CONSOLIDAR]   ✓ Tipo de documento aceito: {tipo_doc}")

                            if key not in resultado_consolidado["requisicoes"][0]["requisicao"]:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key] = []
                                print(f"[CONSOLIDAR]   ✓ Criado array vazio para itens_exame")

                            # Adicionar apenas se ainda não tiver exames (evitar duplicatas)
                            if len(resultado_consolidado["requisicoes"][0]["requisicao"][key]) == 0:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key].extend(value)
                                print(f"[CONSOLIDAR]  ✅ Adicionados {len(value)} exames do {tipo_doc}: {imagem_nome}")
                            else:
                                print(f"[CONSOLIDAR]  ⚠️ Ignorando exames duplicados da imagem: {imagem_nome}")
                        else:
                            print(f"[CONSOLIDAR]   ❌ Tipo de documento NÃO aceito ou array vazio: {tipo_doc}, len={len(value)}")
                    else:
                        # 🆕 MESCLAGEM INTELIGENTE para campos não-exame
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
                    # Enriquecer exames usando mapeamento automático (sem banco de dados)
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
                            # Mapeamento automático por categoria
                            exame_enriquecido["idExame"] = cod_automatico
                            exame_enriquecido["categoria"] = tipo_identificado
                            exame_enriquecido["encontrado"] = True
                            exame_enriquecido["mapeamento_automatico"] = True
                            print(f"[CONSOLIDAR]  {nome_exame} → ID: {cod_automatico} ({tipo_identificado})")
                        else:
                            exame_enriquecido["encontrado"] = False
                            print(f"[CONSOLIDAR]  {nome_exame} não identificado")

                        # Manter campos originais do OCR
                        if isinstance(itens_exame[idx], dict):
                            for k, v in itens_exame[idx].items():
                                if k not in exame_enriquecido:
                                    exame_enriquecido[k] = v

                        exames_enriquecidos.append(exame_enriquecido)

                    # Substituir lista original pela enriquecida
                    resultado_consolidado["requisicoes"][0]["requisicao"]["itens_exame"] = exames_enriquecidos
                    print(f"[CONSOLIDAR]  Exames enriquecidos com mapeamento automático (sem banco de dados)")
            else:
                print(f"[CONSOLIDAR]  AVISO: itens_exame está vazio ou não é uma lista válida!")
        else:
            print(f"[CONSOLIDAR]  AVISO: Campo itens_exame não existe em requisicao!")

        # ADICIONAR DADOS DA API (BANCO DE DADOS) - com menor prioridade que OCR
        if dados_api:
            logger.info("[CONSOLIDAR] Adicionando dados da API ao resultado consolidado...")
            logger.debug(f"[CONSOLIDAR] Tipo de dados_api: {type(dados_api)}")
            logger.debug(f"[CONSOLIDAR] Conteúdo de dados_api: {dados_api}")

            # Verificar se dados_api é um dicionário válido
            if not isinstance(dados_api, dict):
                logger.error(f"[CONSOLIDAR] ERRO: dados_api não é um dicionário, é {type(dados_api)}")
                dados_api = {}  # Usar dicionário vazio para evitar erro

            # Se não há resultados OCR, adicionar alerta
            if len(resultados_ocr) == 0:
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["alertas_processamento"] = "Dados extraídos apenas da API - Sem imagens para processar OCR"
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

                # 🆕 TODOS OS 16 CAMPOS DO PACIENTE (expandido para incluir todos os campos do banco)
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
                    # 🆕 FALLBACK INTELIGENTE: Usar API se campo não existe OU se existe mas está vazio
                    pac_ocr = resultado_consolidado["requisicoes"][0]["paciente"].get(campo)
                    campo_vazio_no_ocr = (pac_ocr is None or
                                         pac_ocr.get("valor") is None or
                                         pac_ocr.get("valor") == '' or
                                         pac_ocr.get("valor") == 'null')

                    # Só adicionar se:
                    # 1. Campo não existe no OCR, OU
                    # 2. Campo existe no OCR mas está vazio
                    # E o valor da API não é None
                    if (campo not in resultado_consolidado["requisicoes"][0]["paciente"] or campo_vazio_no_ocr) and valor:
                        resultado_consolidado["requisicoes"][0]["paciente"][campo] = {
                            "valor": valor,
                            "fonte": "API/DB",
                            "confianca": 1.0
                        }
                        logger.debug(f"[CONSOLIDAR] ✓ Adicionado (fallback): {campo} = {valor}")

                # 🆕 PROCESSAR DATA DE NASCIMENTO / IDADE FORMATADA
                # Se o campo DtaNascimento contém idade formatada ("48 anos 10 meses 10 dias"),
                # calcular a data de nascimento real
                if 'DtaNascimento' in resultado_consolidado["requisicoes"][0]["paciente"]:
                    dta_nasc_obj = resultado_consolidado["requisicoes"][0]["paciente"]['DtaNascimento']
                    if isinstance(dta_nasc_obj, dict):
                        dta_nasc_valor = dta_nasc_obj.get('valor')

                        # Verificar se é idade formatada (contém "anos")
                        if dta_nasc_valor and isinstance(dta_nasc_valor, str) and 'anos' in dta_nasc_valor.lower():
                            logger.info(f"[CONSOLIDAR] 🎂 Detectada idade formatada: {dta_nasc_valor}")

                            # Calcular data de nascimento a partir da idade
                            data_calculada = calcular_data_nascimento_por_idade(dta_nasc_valor)

                            if data_calculada:
                                # Atualizar com a data calculada
                                resultado_consolidado["requisicoes"][0]["paciente"]['DtaNascimento'] = {
                                    "valor": data_calculada,
                                    "fonte": f"Calculado de idade: {dta_nasc_valor}",
                                    "confianca": 0.85  # Confiança um pouco menor pois é calculado
                                }
                                logger.info(f"[CONSOLIDAR] ✅ Data de nascimento calculada: {data_calculada}")
                            else:
                                logger.warning(f"[CONSOLIDAR] ⚠️ Não foi possível calcular data de '{dta_nasc_valor}'")

                # Endereço do paciente - 🆕 COM FALLBACK INTELIGENTE
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
                        # 🆕 FALLBACK: Usar API se campo não existe OU está vazio
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

            # Dados do Médico da API - 🆕 COM FALLBACK INTELIGENTE
            if 'medico' in dados_api and isinstance(dados_api['medico'], dict):
                med_api = dados_api['medico']
                logger.debug(f"[CONSOLIDAR] Processando dados do médico da API: {med_api}")

                campos_medico = {
                    'NomMedico': med_api.get('nome'),
                    'numConselho': med_api.get('crm'),
                    'ufConselho': med_api.get('uf'),
                    'tipoConselho': 'CRM'
                }

                for campo, valor in campos_medico.items():
                    # 🆕 FALLBACK: Usar API se campo não existe OU está vazio
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
                        logger.debug(f"[CONSOLIDAR] ✓ Adicionado (fallback): {campo} = {valor}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de médico na API")

            # Dados da Requisição da API - 🆕 COM FALLBACK INTELIGENTE
            if 'requisicao' in dados_api and isinstance(dados_api['requisicao'], dict):
                req_api = dados_api['requisicao']
                logger.debug(f"[CONSOLIDAR] Processando dados da requisição da API: {req_api}")

                campos_requisicao = {
                    'dtaColeta': req_api.get('dtaColeta'),
                    'dadosClinicos': req_api.get('dadosClinicos'),
                    'numGuia': req_api.get('numGuia')
                }

                for campo, valor in campos_requisicao.items():
                    # 🆕 FALLBACK: Usar API se campo não existe OU está vazio
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
                        logger.debug(f"[CONSOLIDAR] ✓ Adicionado (fallback): {campo} = {valor}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de requisição na API")

            # 🆕 Dados do Convênio da API
            if 'convenio' in dados_api and isinstance(dados_api['convenio'], dict):
                conv_api = dados_api['convenio']
                logger.debug(f"[CONSOLIDAR] Processando dados do convênio da API: {conv_api}")

                nome_convenio = conv_api.get('nome')
                # Só adicionar se tiver valor válido (não fallback com "Convênio ID")
                if nome_convenio and not nome_convenio.startswith('Convênio ID'):
                    resultado_consolidado["requisicoes"][0]["convenio"]['nome'] = {
                        "valor": nome_convenio,
                        "fonte": "API/apLIS/CSV",
                        "confianca": 1.0
                    }
                    logger.debug(f"[CONSOLIDAR] ✓ Adicionado convênio: {nome_convenio}")
                else:
                    logger.debug(f"[CONSOLIDAR] Convênio sem dados válidos: {nome_convenio}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de convênio na API")

            # 🆕 Dados da Fonte Pagadora da API
            if 'fontePagadora' in dados_api and isinstance(dados_api['fontePagadora'], dict):
                fonte_api = dados_api['fontePagadora']
                logger.debug(f"[CONSOLIDAR] Processando dados da fonte pagadora da API: {fonte_api}")

                nome_fonte = fonte_api.get('nome')
                # Só adicionar se tiver valor válido (não fallback com "Local ID" ou "Fonte Pagadora ID")
                if nome_fonte and not nome_fonte.startswith('Local ID') and not nome_fonte.startswith('Fonte Pagadora ID'):
                    resultado_consolidado["requisicoes"][0]["fontePagadora"] = {
                        'nome': {
                            "valor": nome_fonte,
                            "fonte": "API/apLIS/CSV",
                            "confianca": 1.0
                        }
                    }
                    logger.debug(f"[CONSOLIDAR] ✓ Adicionado fonte pagadora: {nome_fonte}")
                else:
                    logger.debug(f"[CONSOLIDAR] Fonte pagadora sem dados válidos: {nome_fonte}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de fonte pagadora na API")

            # 🆕 Dados do Local de Origem da API
            if 'localOrigem' in dados_api and isinstance(dados_api['localOrigem'], dict):
                local_api = dados_api['localOrigem']
                logger.debug(f"[CONSOLIDAR] Processando dados do local de origem da API: {local_api}")

                nome_local = local_api.get('nome')
                # Só adicionar se tiver valor válido (não fallback com "Local ID")
                if nome_local and not nome_local.startswith('Local ID') and not nome_local.startswith('Local não'):
                    resultado_consolidado["requisicoes"][0]["localOrigem"] = {
                        'nome': {
                            "valor": nome_local,
                            "fonte": "API/apLIS/CSV",
                            "confianca": 1.0
                        }
                    }
                    logger.debug(f"[CONSOLIDAR] ✓ Adicionado local de origem: {nome_local}")

                    # Também adicionar em comentarios_gerais
                    resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["NomeLocalOrigem"] = nome_local
                else:
                    logger.debug(f"[CONSOLIDAR] Local de origem sem dados válidos: {nome_local}")
            else:
                logger.debug("[CONSOLIDAR] Nenhum dado de local de origem na API")

            # 🆕 ADICIONAR STATUS APLIS (StatusExame)
            # Esse campo indica o status da requisição no apLIS: 0=Em andamento, 1=Concluído, 2=Cancelado
            if 'requisicao' in dados_api and isinstance(dados_api['requisicao'], dict):
                status_exame = dados_api['requisicao'].get('StatusExame')
                if status_exame is not None:
                    resultado_consolidado["requisicoes"][0]["StatusExame"] = status_exame
                    logger.debug(f"[CONSOLIDAR] ✓ Adicionado StatusExame: {status_exame}")
            # Fallback: tentar diretamente do nível superior
            elif 'StatusExame' in dados_api:
                status_exame = dados_api.get('StatusExame')
                if status_exame is not None:
                    resultado_consolidado["requisicoes"][0]["StatusExame"] = status_exame
                    logger.debug(f"[CONSOLIDAR] ✓ Adicionado StatusExame (nivel superior): {status_exame}")

        # 🆕 SINCRONIZAÇÃO AUTOMÁTICA 0085 ↔ 0200
        # Se detectou múltiplos códigos na mesma imagem, criar requisições duplicadas com dados idênticos
        print(f"\n[CONSOLIDAR] 🔄 Verificando sincronização 0085 ↔ 0200...")
        print(f"[CONSOLIDAR] Códigos encontrados: {codigos_encontrados}")

        # Identificar pares 0085/0200
        codigos_0085 = [c for c in codigos_encontrados if c.startswith('0085')]
        codigos_0200 = [c for c in codigos_encontrados if c.startswith('0200')]

        print(f"[CONSOLIDAR] Requisições 0085: {codigos_0085}")
        print(f"[CONSOLIDAR] Requisições 0200: {codigos_0200}")

        # Se encontrou AMBOS os tipos (0085 E 0200), criar requisições duplicadas
        if len(codigos_0085) > 0 and len(codigos_0200) > 0:
            print(f"[CONSOLIDAR] ✅ Detectado par 0085/0200 na mesma imagem!")
            print(f"[CONSOLIDAR] �� Criando requisições sincronizadas com dados idênticos...")

            # Pegar a requisição consolidada como base
            requisicao_base = resultado_consolidado["requisicoes"][0].copy()

            # Criar lista de requisições (uma para cada código)
            requisicoes_sincronizadas = []

            # Combinar todos os códigos encontrados
            todos_codigos = sorted(list(codigos_encontrados))

            for idx, codigo in enumerate(todos_codigos):
                # Fazer cópia profunda da requisição base
                import copy
                req_sincronizada = copy.deepcopy(requisicao_base)

                # Atualizar o código da requisição
                req_sincronizada["comentarios_gerais"]["requisicao_entrada"] = codigo

                # Adicionar metadata de sincronização
                req_sincronizada["comentarios_gerais"]["sincronizacao_0085_0200"] = {
                    "sincronizado": True,
                    "tipo_requisicao": "0085" if codigo.startswith('0085') else "0200",
                    "par_encontrado": todos_codigos,
                    "dados_identicos": True,
                    "fonte_sincronizacao": "OCR - Mesma imagem"
                }

                requisicoes_sincronizadas.append(req_sincronizada)
                print(f"[CONSOLIDAR]   ✓ Requisição {idx+1}/{len(todos_codigos)}: {codigo}")

            # Substituir array de requisições
            resultado_consolidado["requisicoes"] = requisicoes_sincronizadas
            resultado_consolidado["metadata"]["total_requisicoes"] = len(requisicoes_sincronizadas)

            print(f"[CONSOLIDAR] ✅ Criadas {len(requisicoes_sincronizadas)} requisições sincronizadas")
            print(f"[CONSOLIDAR] 🎯 Dados de paciente, médico e convênio são IDÊNTICOS em todas")
        else:
            print(f"[CONSOLIDAR] ℹ️ Apenas um tipo de requisição detectado (sem sincronização)")

        # LOG FINAL - Mostrar resumo do que foi consolidado
        print(f"\n[CONSOLIDAR] ===== RESUMO DA CONSOLIDAÇÃO =====")
        print(f"[CONSOLIDAR] Total de imagens processadas: {len(resultados_ocr)}")
        print(f"[CONSOLIDAR] Dados da API incluídos: {bool(dados_api)}")
        print(f"[CONSOLIDAR] Total de requisições geradas: {len(resultado_consolidado['requisicoes'])}")

        for idx, req in enumerate(resultado_consolidado['requisicoes']):
            cod_req = req["comentarios_gerais"].get("requisicao_entrada", "N/A")
            print(f"[CONSOLIDAR] --- Requisição {idx+1}: {cod_req} ---")
            print(f"[CONSOLIDAR]   Campos no paciente: {len(req['paciente'])}")
            print(f"[CONSOLIDAR]   Campos no medico: {len(req['medico'])}")
            print(f"[CONSOLIDAR]   Campos no convenio: {len(req['convenio'])}")
            print(f"[CONSOLIDAR]   Campos na requisicao: {len(req['requisicao'])}")

        print(f"[CONSOLIDAR] =====================================\n")

        # 🆕 SALVAR AUTOMATICAMENTE NO SUPABASE - TODAS AS REQUISIÇÕES SINCRONIZADAS
        print(f"[CONSOLIDAR] 🔍 Debug Supabase:")
        print(f"[CONSOLIDAR]   - SUPABASE_ENABLED: {SUPABASE_ENABLED}")
        print(f"[CONSOLIDAR]   - Total de requisições para salvar: {len(resultado_consolidado['requisicoes'])}")
        print(f"[CONSOLIDAR]   - supabase_manager: {supabase_manager is not None}")

        if SUPABASE_ENABLED and len(resultado_consolidado['requisicoes']) > 0:
            try:
                # Salvar TODAS as requisições (0085 e 0200 se houver sincronização)
                for idx, req_dados in enumerate(resultado_consolidado['requisicoes']):
                    cod_req = req_dados["comentarios_gerais"].get("requisicao_entrada")

                    if not cod_req:
                        print(f"[CONSOLIDAR] ⚠️ Requisição {idx+1} sem código, pulando...")
                        continue

                    print(f"[CONSOLIDAR] 💾 Salvando requisição {idx+1}/{len(resultado_consolidado['requisicoes'])}: {cod_req}")

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
                        dados_consolidados=req_dados,  # Salvar dados específicos desta requisição
                        exames=exames_list,
                        exames_ids=exames_ids,
                        processado_por='sistema_ocr'
                    )

                    if resultado_save.get('sucesso') == 1:
                        print(f"[CONSOLIDAR] ✅ Requisição {cod_req} salva no Supabase! (Ação: {resultado_save.get('acao')})")
                    else:
                        print(f"[CONSOLIDAR] ⚠️ Erro ao salvar requisição {cod_req}: {resultado_save.get('erro')}")

                print(f"[CONSOLIDAR] ✅ Finalizado salvamento de {len(resultado_consolidado['requisicoes'])} requisições")

            except Exception as e:
                # Não quebrar o fluxo se der erro no Supabase
                print(f"[CONSOLIDAR] ⚠️ Erro ao salvar no Supabase (continuando): {str(e)}")
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
    Busca IDs de exames no banco de dados a partir dos nomes extraídos pelo OCR
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

            # Identificar tipo de exame usando a função global (baseado em categorias)
            tipo_identificado, cod_automatico = identificar_tipo_exame_backend(nome_limpo)
            print(f"[BUSCAR EXAMES] Tipo identificado: {tipo_identificado} (CodExame: {cod_automatico})")

            # Usar mapeamento automático por categoria
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
                print(f"[BUSCAR EXAMES]  Mapeado por categoria: {nome_exame} → ID: {cod_automatico} ({tipo_identificado})")
            else:
                resultados.append({
                    "nome_ocr": nome_exame,
                    "idExame": None,
                    "tipo_identificado": tipo_identificado,
                    "encontrado": False,
                    "mensagem": f"Exame '{nome_exame}' não identificado por categoria"
                })
                print(f"[BUSCAR EXAMES]  Não identificado: {nome_exame} (categoria: {tipo_identificado})")

        # Contar quantos foram encontrados
        encontrados = sum(1 for r in resultados if r['encontrado'])

        # Gerar string de IDs para o campo EXAMES CONVÊNIO (separados por vírgula)
        ids_encontrados = [str(r['idExame']) for r in resultados if r['encontrado'] and r['idExame']]
        ids_string = ", ".join(ids_encontrados)

        # Gerar string de nomes para registro/visualização
        nomes_encontrados = [r['nome_ocr'] for r in resultados if r['encontrado']]
        nomes_string = ", ".join(nomes_encontrados)

        print(f"[BUSCAR EXAMES] IDs encontrados: {ids_string}")
        print(f"[BUSCAR EXAMES] Nomes dos exames: {nomes_string}")

        return jsonify({
            "sucesso": 1,
            "total_solicitado": len(nomes_exames),
            "total_encontrado": encontrados,
            "ids_string": ids_string,  # String pronta para campo "EXAMES CONVÊNIO"
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
    Limpa todas as imagens temporárias ao iniciar o servidor
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
    """Lista todos os médicos do CSV"""
    try:
        medicos_lista = list(MEDICOS_CACHE.values())
        return jsonify({
            "sucesso": 1,
            "total": len(medicos_lista),
            "medicos": medicos_lista
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar médicos: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/medicos/<crm>/<uf>', methods=['GET'])
def buscar_medico(crm, uf):
    """Busca médico por CRM e UF"""
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
                "erro": f"Médico CRM {crm}/{uf} não encontrado"
            }), 404
    except Exception as e:
        logger.error(f"[API] Erro ao buscar médico: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/convenios', methods=['GET'])
def listar_convenios():
    """Lista todos os convênios do CSV"""
    try:
        convenios_lista = list(CONVENIOS_CACHE.values())
        return jsonify({
            "sucesso": 1,
            "total": len(convenios_lista),
            "convenios": convenios_lista
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar convênios: {e}")
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

@app.route('/api/instituicoes', methods=['GET'])
def listar_instituicoes():
    """Lista todas as instituições do CSV"""
    try:
        instituicoes_lista = list(INSTITUICOES_CACHE.values())
        return jsonify({
            "sucesso": 1,
            "total": len(instituicoes_lista),
            "instituicoes": instituicoes_lista
        }), 200
    except Exception as e:
        logger.error(f"[API] Erro ao listar instituições: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500

@app.route('/api/instituicoes/<id_instituicao>', methods=['GET'])
def buscar_instituicao_endpoint(id_instituicao):
    """Busca instituição por ID"""
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
                "erro": f"Instituição ID {id_instituicao} não encontrada"
            }), 404
    except Exception as e:
        logger.error(f"[API] Erro ao buscar instituição: {e}")
        return jsonify({"sucesso": 0, "erro": str(e)}), 500


# ============================================
# ROTAS DO SUPABASE - HISTÓRICO DE REQUISIÇÕES
# ============================================

@app.route('/api/historico/salvar', methods=['POST'])
def salvar_requisicao_historico():
    """
    Salva uma requisição processada no histórico (Supabase)

    Body:
        - cod_requisicao (obrigatório)
        - dados_paciente (obrigatório)
        - dados_ocr (opcional)
        - dados_consolidados (opcional)
        - exames (opcional): lista de nomes
        - exames_ids (opcional): lista de IDs
    """
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase não está configurado"
        }), 503

    try:
        dados = request.json

        if not dados.get('cod_requisicao'):
            return jsonify({
                "sucesso": 0,
                "erro": "Código da requisição é obrigatório"
            }), 400

        if not dados.get('dados_paciente'):
            return jsonify({
                "sucesso": 0,
                "erro": "Dados do paciente são obrigatórios"
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
    """Busca uma requisição específica no histórico"""
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase não está configurado"
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
    """Lista requisições recentes do histórico"""
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase não está configurado"
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
    """Busca requisições por CPF do paciente"""
    if not SUPABASE_ENABLED:
        return jsonify({
            "sucesso": 0,
            "erro": "Supabase não está configurado"
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
    DEPRECATED: Use /api/buscar-paciente ao invés desta rota
    Busca paciente no banco de dados MySQL pelo CPF
    Retorna o CodPaciente e dados básicos do paciente
    """
    return buscar_paciente()  # Redireciona para a nova função


@app.route('/api/buscar-paciente', methods=['POST'])
def buscar_paciente():
    """
    Busca paciente no banco de dados MySQL pelo CPF ou Nome Completo
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
                "erro": "CPF ou Nome não fornecido"
            }), 400

        # Conectar ao banco
        connection = pymysql.connect(**DB_CONFIG)
        if not connection:
            logger.error(f"[BUSCAR_PACIENTE] ❌ Erro ao conectar no banco de dados")
            return jsonify({
                "sucesso": 0,
                "erro": "Erro ao conectar no banco de dados"
            }), 500

        try:
            with connection.cursor() as cursor:
                # Buscar por CPF
                if cpf:
                    cpf_limpo = ''.join(filter(str.isdigit, cpf))
                    logger.info(f"[BUSCAR_PACIENTE] 🔍 Buscando paciente com CPF: {cpf_limpo}")
                    
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
                    logger.info(f"[BUSCAR_PACIENTE] 🔍 Buscando paciente com Nome: {nome_limpo}")
                    
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

                    logger.info(f"[BUSCAR_PACIENTE] ✅ Paciente encontrado no banco!")
                    logger.info(f"[BUSCAR_PACIENTE]   CodPaciente: {cod_paciente}")
                    logger.info(f"[BUSCAR_PACIENTE]   Nome: {nome_paciente}")
                    logger.info(f"[BUSCAR_PACIENTE]   CPF: {cpf_db}")

                    # Buscar dados completos do paciente
                    dados_completos = buscar_dados_completos_paciente(cod_paciente)

                    return jsonify({
                        "sucesso": 1,
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
                else:
                    criterio = f"CPF {cpf_limpo}" if cpf else f"Nome '{nome_limpo}'"
                    logger.warning(f"[BUSCAR_PACIENTE] ⚠️ Paciente com {criterio} não encontrado no banco")
                    return jsonify({
                        "sucesso": 0,
                        "erro": f"Paciente com {criterio} não encontrado no sistema"
                    }), 404

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"[BUSCAR_PACIENTE] ❌ Exceção: {str(e)}")
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

        # Validar campos obrigatórios
        nome = dados.get('nome')
        cpf = dados.get('cpf')
        data_nascimento = dados.get('dataNascimento') or dados.get('dtaNasc')

        if not nome:
            return jsonify({
                "sucesso": 0,
                "erro": "Nome do paciente é obrigatório"
            }), 400

        if not cpf:
            return jsonify({
                "sucesso": 0,
                "erro": "CPF é obrigatório para criar novo paciente"
            }), 400

        # Limpar CPF
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_limpo) != 11:
            return jsonify({
                "sucesso": 0,
                "erro": "CPF inválido (deve ter 11 dígitos)"
            }), 400

        logger.info(f"[CRIAR_PACIENTE] Verificando se CPF {cpf_limpo} já existe no banco...")

        # 1. VERIFICAR SE JÁ EXISTE PACIENTE COM ESTE CPF
        try:
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                query = "SELECT CodPaciente, NomPaciente FROM newdb.paciente WHERE CPF = %s LIMIT 1"
                cursor.execute(query, (cpf_limpo,))
                resultado = cursor.fetchone()

                if resultado:
                    cod_paciente_existente = resultado[0]
                    nome_existente = resultado[1]
                    logger.warning(f"[CRIAR_PACIENTE] ⚠️ Paciente com CPF {cpf_limpo} já existe: ID {cod_paciente_existente} - {nome_existente}")
                    connection.close()
                    return jsonify({
                        "sucesso": 0,
                        "erro": f"Paciente com este CPF já cadastrado: {nome_existente} (ID: {cod_paciente_existente})",
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
        logger.info(f"[CRIAR_PACIENTE] 🔍 Validando CPF {cpf_limpo} na Receita Federal...")
        dados_receita = consultar_cpf_receita_federal(cpf_limpo, data_nascimento)

        usa_metodo_sem_cpf = False
        
        if not dados_receita or not dados_receita.get('valido'):
            logger.warning(f"[CRIAR_PACIENTE] ⚠️ CPF {cpf_limpo} não validado pela Receita Federal")
            logger.info(f"[CRIAR_PACIENTE] 🔄 Usando método alternativo: Paciente sem documento (CPF não validado)")
            usa_metodo_sem_cpf = True
        else:
            logger.info(f"[CRIAR_PACIENTE] ✅ CPF validado pela Receita Federal!")
            logger.info(f"[CRIAR_PACIENTE]   Nome na RF: {dados_receita.get('nome')}")
            logger.info(f"[CRIAR_PACIENTE]   Data Nasc: {dados_receita.get('data_nascimento')}")

        # 3. CRIAR PACIENTE NO apLIS
        if usa_metodo_sem_cpf:
            logger.info(f"[CRIAR_PACIENTE] 📝 Criando paciente com método 'Sem Documento'...")
            logger.warning(f"[CRIAR_PACIENTE] ⚠️ ATENÇÃO: CPF {cpf_limpo} NÃO FOI VALIDADO na Receita Federal")
        else:
            logger.info(f"[CRIAR_PACIENTE] 📝 Criando paciente no apLIS...")

        # Montar estrutura para o apLIS
        dat = {
            "idEvento": "3",  # Evento de inclusão de paciente
            "nome": nome
        }
        
        # Se CPF foi validado, enviar CPF. Se não, usar cpfAusente
        if usa_metodo_sem_cpf:
            dat["cpfAusente"] = "1"  # Paciente sem documento
            logger.warning(f"[CRIAR_PACIENTE] ⚠️ CPF {cpf_limpo} não validado - usando cpfAusente")
        else:
            dat["cpf"] = cpf_limpo

        # Adicionar campos opcionais se fornecidos
        if data_nascimento:
            # Converter para formato do apLIS se necessário
            if 'T' in data_nascimento:
                data_nascimento = data_nascimento.split('T')[0]
            dat['dtaNascimento'] = data_nascimento
        elif dados_receita and dados_receita.get('data_nascimento'):
            # Usar data da Receita Federal (só se validou)
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
            logger.info(f"[CRIAR_PACIENTE] ✅ Paciente criado com sucesso! CodPaciente: {cod_paciente}")
            
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
            
            # Adicionar aviso se usou método alternativo
            if usa_metodo_sem_cpf:
                resposta_final["aviso"] = {
                    "tipo": "cpf_nao_validado",
                    "mensagem": f"⚠️ ATENÇÃO: Paciente cadastrado com método alternativo (CPF {cpf_limpo} não foi validado na Receita Federal). Verifique os dados do paciente.",
                    "cpf": cpf_limpo
                }
                logger.warning(f"[CRIAR_PACIENTE] ⚠️ Retornando aviso de CPF não validado: {cpf_limpo}")
            
            return jsonify(resposta_final), 201
        else:
            erro_msg = resposta.get("dat", {}).get("msg", "Erro desconhecido")
            logger.error(f"[CRIAR_PACIENTE] ❌ Erro ao criar paciente: {erro_msg}")
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
            "idEvento": "4",  # Evento de alteração de paciente
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
            # Só envia se for válido: 9 dígitos e não só zeros
            num_guia = str(dados['numGuia']).strip()
            num_guia_limpo = ''.join(filter(str.isdigit, num_guia))
            
            if num_guia_limpo and len(num_guia_limpo) == 9 and num_guia_limpo != '000000000':
                dat['numGuiaConvenio'] = num_guia_limpo
                logger.info(f"[ATUALIZAR_PACIENTE] ✅ numGuia válido, será enviado: {num_guia_limpo}")
            else:
                logger.info(f"[ATUALIZAR_PACIENTE] ℹ️ numGuia inválido ('{num_guia_limpo}'), não será enviado")
        if dados.get('endereco'):
            dat['endereco'] = dados['endereco']

        logger.info(f"[ATUALIZAR_PACIENTE] Chamando apLIS com dados: {dat}")

        # Chamar o apLIS para atualizar
        resposta = fazer_requisicao_aplis("pacienteAlterar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            logger.info(f"[ATUALIZAR_PACIENTE] ✅ Paciente atualizado com sucesso")
            return jsonify({
                "sucesso": 1,
                "mensagem": "Dados do paciente atualizados com sucesso"
            }), 200
        else:
            erro_msg = resposta.get("dat", {}).get("msg", "Erro desconhecido")
            logger.error(f"[ATUALIZAR_PACIENTE] ❌ Erro: {erro_msg}")
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
    """Atualiza dados de uma requisição"""
    try:
        dados = request.get_json()
        logger.info(f"[ATUALIZAR_REQUISICAO] Código: {cod_requisicao}, Dados: {dados}")

        # Montar estrutura para o apLIS
        dat = {
            "idEvento": "51",  # Evento de alteração de requisição
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
            # Só envia se for válido: 9 dígitos e não só zeros
            num_guia = str(dados['numGuia']).strip()
            num_guia_limpo = ''.join(filter(str.isdigit, num_guia))
            
            if num_guia_limpo and len(num_guia_limpo) == 9 and num_guia_limpo != '000000000':
                dat['numGuia'] = num_guia_limpo
                logger.info(f"[ATUALIZAR_REQUISICAO] ✅ numGuia válido, será enviado: {num_guia_limpo}")
            else:
                logger.info(f"[ATUALIZAR_REQUISICAO] ℹ️ numGuia inválido ('{num_guia_limpo}'), não será enviado")
        if dados.get('dadosClinicos'):
            dat['dadosClinicos'] = dados['dadosClinicos']

        logger.info(f"[ATUALIZAR_REQUISICAO] Chamando apLIS com dados: {dat}")

        # Chamar o apLIS para atualizar
        resposta = fazer_requisicao_aplis("requisicaoAlterar", dat)

        if resposta.get("dat", {}).get("sucesso") == 1:
            logger.info(f"[ATUALIZAR_REQUISICAO] ✅ Requisição atualizada com sucesso")
            return jsonify({
                "sucesso": 1,
                "mensagem": "Dados da requisição atualizados com sucesso"
            }), 200
        else:
            erro_msg = resposta.get("dat", {}).get("msg", "Erro desconhecido")
            logger.error(f"[ATUALIZAR_REQUISICAO] ❌ Erro: {erro_msg}")
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


if __name__ == '__main__':
    # Limpar imagens temporárias ao iniciar
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
    logger.info("  GET  /api/medicos                - Listar todos os médicos (CSV)")
    logger.info("  GET  /api/medicos/<crm>/<uf>     - Buscar médico por CRM/UF")
    logger.info("  GET  /api/convenios              - Listar todos os convênios (CSV)")
    logger.info("  GET  /api/convenios/<id>         - Buscar convênio por ID")
    logger.info("  GET  /api/instituicoes           - Listar todas as instituições (CSV)")
    logger.info("  GET  /api/instituicoes/<id>      - Buscar instituição por ID")
    logger.info("")
    logger.info("METODOLOGIA ATUALIZADA:")
    logger.info("  - Usando fazer_requisicao_aplis() para todas as chamadas ao apLIS")
    logger.info("  - Suporte a requisicaoListar para listagem de requisições")
    logger.info("  - Logging detalhado de todas as requisições e respostas")
    logger.info("  - Criação automática de pacientes com validação CPF na Receita Federal")
    logger.info("")
    logger.info("CORS configurado para aceitar requisições de qualquer origem")
    logger.info("URLs dinamicas habilitadas (funciona com localhost e ngrok)")
    logger.info("Logging completo habilitado (console + arquivo)")
    logger.info("")
    logger.info("HISTÓRICO DE REQUISIÇÕES (SUPABASE):")
    if SUPABASE_ENABLED:
        logger.info("  [OK] Supabase HABILITADO - Histórico disponível")
        logger.info("  - Salvamento automático após análise OCR")
        logger.info("  - Status atualizado após salvar admissão")
        logger.info("  - Endpoints: /api/historico/listar, /api/historico/<cod>, /api/historico/buscar-cpf/<cpf>")
    else:
        logger.warning("  [AVISO] Supabase DESABILITADO - Histórico não disponível")
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
