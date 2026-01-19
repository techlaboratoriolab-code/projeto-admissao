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

# Carregar variáveis de ambiente do arquivo .env na pasta backend
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

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

# Configurações apLIS
APLIS_URL = "https://lab.aplis.inf.br/api/integracao.php"
APLIS_USERNAME = "api.lab"
APLIS_PASSWORD = "nintendo64"
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
    logger.debug(f"[apLIS] Enviando requisição: {cmd}")
    logger.debug(f"[apLIS] Payload: {json.dumps(payload, indent=2, ensure_ascii=False)[:500]}")

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
            logger.debug(f"[apLIS] Resposta JSON: {json.dumps(resposta_json, indent=2, ensure_ascii=False)[:500]}")

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


def salvar_admissao_aplis(dados_admissao):
    """
    Salva uma admissão/requisição no apLIS usando a nova metodologia genérica
    """
    logger.info(f"[Admissão] Salvando admissão com dados: {len(str(dados_admissao))} bytes")
    return fazer_requisicao_aplis("admissaoSalvar", dados_admissao)


def listar_requisicoes_aplis(id_evento, periodo_ini, periodo_fim, ordenar="IdRequisicao"):
    """
    Lista requisições do apLIS usando requisicaoListar
    
    Args:
        id_evento (str): ID do evento
        periodo_ini (str): Data inicial (YYYY-MM-DD)
        periodo_fim (str): Data final (YYYY-MM-DD)
        ordenar (str): Campo para ordenação (padrão: IdRequisicao)
    
    Returns:
        dict: Resposta com requisições
    """
    dat = {
        "ordenar": ordenar,
        "idEvento": str(id_evento),
        "periodoIni": periodo_ini,
        "periodoFim": periodo_fim
    }
    
    logger.info(f"[Listagem] Listando requisições do evento {id_evento} de {periodo_ini} a {periodo_fim}")
    return fazer_requisicao_aplis("requisicaoListar", dat)


@app.route('/api/requisicoes/listar', methods=['POST'])
def listar_requisicoes():
    """
    Lista requisições do apLIS usando a metodologia requisicaoListar
    
    Exemplo de requisição:
    {
        "idEvento": "50",
        "periodoIni": "2026-01-15",
        "periodoFim": "2026-01-15",
        "ordenar": "IdRequisicao"
    }
    """
    try:
        dados = request.json
        
        id_evento = dados.get('idEvento')
        periodo_ini = dados.get('periodoIni')
        periodo_fim = dados.get('periodoFim')
        ordenar = dados.get('ordenar', 'IdRequisicao')
        
        if not all([id_evento, periodo_ini, periodo_fim]):
            return jsonify({
                "sucesso": 0,
                "erro": "Campos obrigatórios: idEvento, periodoIni, periodoFim"
            }), 400
        
        logger.info(f"[Listagem] Requisição de listagem: evento={id_evento}, período={periodo_ini} a {periodo_fim}")
        
        resposta = listar_requisicoes_aplis(id_evento, periodo_ini, periodo_fim, ordenar)
        
        return jsonify({
            "sucesso": 1 if resposta.get("dat", {}).get("sucesso") == 1 else 0,
            "dados": resposta.get("dat", {}),
            "mensagem": "Listagem obtida com sucesso" if resposta.get("dat", {}).get("sucesso") == 1 else "Erro ao listar"
        }), 200
        
    except Exception as e:
        logger.error(f"[Listagem] Erro: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao listar requisições: {str(e)}"
        }), 500


@app.route('/api/requisicao/<cod_requisicao>', methods=['GET'])
def buscar_requisicao(cod_requisicao):
    """
    Busca dados completos de uma requisição diretamente do apLIS
    Usando a nova metodologia requisicaoListar - sem dependência de banco local
    """
    try:
        logger.info(f"[Buscar] Buscando requisição: {cod_requisicao}")

        # Buscar no apLIS usando requisicaoListar com filtro por código
        # Usar período amplo para garantir que encontramos a requisição
        hoje = datetime.now()
        periodo_fim = hoje.strftime("%Y-%m-%d")
        periodo_ini = (hoje - timedelta(days=365)).strftime("%Y-%m-%d")  # Buscar último ano

        dat = {
            "ordenar": "CodRequisicao",
            "idEvento": "50",  # ID do evento padrão
            "periodoIni": periodo_ini,
            "periodoFim": periodo_fim,
            "codRequisicao": cod_requisicao
        }

        resposta = fazer_requisicao_aplis("requisicaoListar", dat)

        # Verificar se encontrou a requisição
        if resposta.get("dat", {}).get("sucesso") != 1:
            logger.warning(f"[Buscar] Requisição {cod_requisicao} não encontrada no apLIS")
            logger.debug(f"[Buscar] Resposta completa: {resposta}")
            return jsonify({
                "sucesso": 0,
                "erro": "Requisição não encontrada",
                "codRequisicao": cod_requisicao,
                "detalhes": resposta
            }), 404

        # Dados retornados pelo apLIS (vem em formato de lista)
        dados_resposta = resposta.get("dat", {})
        lista_requisicoes = dados_resposta.get("lista", [])

        if not lista_requisicoes or len(lista_requisicoes) == 0:
            logger.warning(f"[Buscar] Nenhuma requisição encontrada na lista para: {cod_requisicao}")
            return jsonify({
                "sucesso": 0,
                "erro": "Requisição não encontrada",
                "codRequisicao": cod_requisicao
            }), 404

        # Pegar o primeiro item da lista (deve ser a requisição buscada)
        dados_aplis = lista_requisicoes[0]
        logger.info(f"[Buscar] Requisição encontrada no apLIS: {cod_requisicao}")
        logger.debug(f"[Buscar] Dados da requisição: {dados_aplis}")

        # Buscar imagens da AWS S3 e baixar localmente (método original)
        imagens = []
        s3_client = get_s3_client()

        if s3_client:
            try:
                # Determinar prefixo baseado no código da requisição (ex: 0040 dos primeiros 4 dígitos)
                prefixo_lab = cod_requisicao[:4] if len(cod_requisicao) >= 4 else '0040'
                # IMPORTANTE: Buscar apenas imagens que começam com o código completo da requisição
                caminho_s3_base = f"lab/Arquivos/Foto/{prefixo_lab}/{cod_requisicao}"

                logger.info(f"[S3] Buscando imagens em: {caminho_s3_base}")

                # Listar objetos no S3 com o prefixo (apenas imagens dessa requisição específica)
                response_s3 = s3_client.list_objects_v2(
                    Bucket=S3_BUCKET,
                    Prefix=caminho_s3_base
                )

                if 'Contents' in response_s3:
                    for obj in response_s3['Contents']:
                        key = obj['Key']
                        filename = key.split('/')[-1]

                        # Pular se for pasta vazia
                        if not filename:
                            continue

                        # FILTRO ADICIONAL: Verificar se o nome do arquivo começa com o código da requisição
                        if not filename.startswith(cod_requisicao):
                            logger.debug(f"[S3] Pulando arquivo que não pertence a esta requisição: {filename}")
                            continue

                        try:
                            # Caminho local temporário
                            arquivo_local = os.path.join(TEMP_IMAGES_DIR, filename)

                            # Baixar do S3 se não existe localmente
                            if not os.path.exists(arquivo_local):
                                logger.info(f"[S3] Baixando: {key}")
                                s3_client.download_file(S3_BUCKET, key, arquivo_local)
                                logger.info(f"[S3] Salvo em: {arquivo_local}")
                            else:
                                logger.debug(f"[S3] Já existe localmente: {filename}")

                            # URL dinâmica local (funciona com localhost e ngrok)
                            base_url = request.host_url.rstrip('/')
                            url_local = f"{base_url}/api/imagem/{filename}"

                            imagens.append({
                                "nome": filename,
                                "url": url_local,
                                "tamanho": obj['Size'],
                                "dataCadastro": obj['LastModified'].isoformat()
                            })

                        except Exception as e:
                            logger.error(f"[S3] Erro ao processar {filename}: {e}")

                    logger.info(f"[S3] Encontradas {len(imagens)} imagens para requisição {cod_requisicao}")
                else:
                    logger.info(f"[S3] Nenhuma imagem encontrada em {caminho_s3_base}")

            except Exception as e:
                logger.error(f"[S3] Erro ao buscar imagens: {str(e)}")
        else:
            logger.warning("[S3] Cliente S3 não disponível - imagens não serão carregadas")

        # Montar resposta estruturada
        resultado = {
            "sucesso": 1,
            "requisicao": {
                "codRequisicao": dados_aplis.get("CodRequisicao"),
                "idRequisicao": dados_aplis.get("IdRequisicao"),
                "dtaColeta": dados_aplis.get("DtaColeta") or dados_aplis.get("DtaPrevista"),
                "numGuia": dados_aplis.get("NumGuiaConvenio") or dados_aplis.get("NumExterno"),
                "dadosClinicos": dados_aplis.get("IndicacaoClinica"),
                "idConvenio": dados_aplis.get("IdConvenio"),
                "idLocalOrigem": dados_aplis.get("IdLocalOrigem"),
                "idFontePagadora": dados_aplis.get("IdFontePagadora"),
                "idMedico": dados_aplis.get("CodMedico")
            },
            "paciente": {
                "idPaciente": dados_aplis.get("CodPaciente"),
                "nome": dados_aplis.get("NomPaciente"),
                "dtaNasc": dados_aplis.get("DtaNascimento"),
                "sexo": dados_aplis.get("Sexo"),
                "cpf": dados_aplis.get("CPF"),
                "rg": dados_aplis.get("RGNumero"),
                "telCelular": dados_aplis.get("NumTelefone"),
                "endereco": {
                    "cep": dados_aplis.get("CEP"),
                    "logradouro": dados_aplis.get("DesEndereco"),
                    "numEndereco": dados_aplis.get("NumEndereco"),
                    "bairro": dados_aplis.get("Bairro"),
                    "cidade": dados_aplis.get("Cidade"),
                    "uf": dados_aplis.get("Estado")
                }
            },
            "medico": {
                "nome": dados_aplis.get("NomMedico"),
                "crm": dados_aplis.get("CRM"),
                "uf": dados_aplis.get("CRMUF")
            },
            "convenio": {
                "nome": dados_aplis.get("NomeConvenio", f"Convênio ID {dados_aplis.get('IdConvenio')}")
            },
            "fontePagadora": {
                "nome": dados_aplis.get("NomeFontePagadora", f"Fonte Pagadora ID {dados_aplis.get('IdFontePagadora')}")
            },
            "localOrigem": {
                "nome": dados_aplis.get("NomeLocalOrigem", f"Local ID {dados_aplis.get('IdLocalOrigem')}")
            },
            "imagens": imagens,  # Imagens do S3
            "totalImagens": len(imagens),
            "dadosAplis": dados_resposta  # Incluir todos os dados brutos para referência
        }

        logger.info(f"[Buscar] Resposta formatada para: {cod_requisicao} ({len(imagens)} imagens)")
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"[Buscar] Erro ao buscar requisição {cod_requisicao}: {str(e)}")
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro ao buscar requisição: {str(e)}"
        }), 500


@app.route('/api/admissao/salvar', methods=['POST'])
def salvar_admissao():
    """
    Endpoint para salvar admissão
    """
    try:
        dados = request.json

        # Validar campos obrigatórios
        campos_obrigatorios = [
            'idLaboratorio', 'idUnidade', 'idPaciente', 'dtaColeta',
            'idConvenio', 'idLocalOrigem', 'idFontePagadora',
            'idMedico', 'idExame', 'examesConvenio'
        ]

        campos_faltantes = [campo for campo in campos_obrigatorios if campo not in dados]

        if campos_faltantes:
            return jsonify({
                "sucesso": 0,
                "erro": f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}"
            }), 400

        # Chamar apLIS
        resultado = salvar_admissao_aplis(dados)

        if resultado.get("dat", {}).get("sucesso") == 1:
            return jsonify({
                "sucesso": 1,
                "mensagem": "Admissão salva com sucesso!",
                "codRequisicao": resultado["dat"].get("codRequisicao"),
                "dados": resultado["dat"]
            }), 200
        else:
            return jsonify({
                "sucesso": 0,
                "erro": resultado.get("erro", "Erro desconhecido ao salvar admissão"),
                "detalhes": resultado
            }), 500

    except Exception as e:
        return jsonify({
            "sucesso": 0,
            "erro": f"Erro no servidor: {str(e)}"
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
    """
    try:
        dados = request.json
        imagem_nome = dados.get('imagemNome')

        if not imagem_nome:
            return jsonify({"sucesso": 0, "erro": "Nome da imagem não fornecido"}), 400

        # Pegar a imagem do diretório temporário
        arquivo_path = os.path.join(TEMP_IMAGES_DIR, imagem_nome)

        if not os.path.exists(arquivo_path):
            return jsonify({"sucesso": 0, "erro": "Imagem não encontrada no servidor"}), 404

        print(f"[OCR] Processando imagem: {imagem_nome}")

        # Ler a imagem
        with open(arquivo_path, 'rb') as f:
            image_bytes = f.read()

        # Criar modelo Gemini
        model = GenerativeModel("gemini-2.0-flash-exp")

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

        print(f"[OCR] Usando mime_type: {mime_type}")

        # Criar parte da imagem/documento
        image_part = Part.from_data(data=image_bytes, mime_type=mime_type)

        # Prompt para extrair dados com rastreabilidade
        prompt = f"""
Voce e um Especialista em OCR de Alta Precisao para Documentos Medicos e de Identificacao.

MISSAO: EXTRAIR DADOS COM MAXIMA PRECISAO - CADA CARACTERE IMPORTA!


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

 PEDIDO MÉDICO:
   - NOME PACIENTE: Início do documento, campo "Paciente"
   - EXAME SOLICITADO: "Procedimento", "Exame", "Especificação da Amostra"
   - MÉDICO: Nome e CRM do solicitante
   - DATA COLETA: "Data da coleta", "Data"
   - DADOS CLÍNICOS: Campo "Dados Clínicos", "Informações Clínicas"

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

ONDE PROCURAR A DATA DE NASCIMENTO:
1. Procure pelas palavras: "DATA DE NASCIMENTO", "NASCIMENTO", "NATURALIDADE"
2. Na carteira da OAB, geralmente está NA PARTE SUPERIOR do documento
3. Está sempre em formato de data: DD/MM/YYYY ou DD/MM/YY

FORMATOS QUE VOCÊ VAI ENCONTRAR NO DOCUMENTO:
- 17/02/1985 (dia/mês/ano com 4 dígitos)
- 17/02/85 (dia/mês/ano com 2 dígitos)
- 17.02.1985 (com pontos ao invés de barras)
- 17 FEV 1985 (com mês por extenso)
- 17-02-1985 (com traços)

COMO CONVERTER:
1. Identifique o dia, mês e ano
2. Converta para formato: YYYY-MM-DD
3. Se ano tem 2 dígitos (85), adicione 19 na frente (1985)
4. Anos entre 00-30 são 2000+ (ex: 25 = 2025)
5. Anos entre 31-99 são 1900+ (ex: 85 = 1985)

EXEMPLOS DE CONVERSÃO:
- "17/02/1985" → "1985-02-17"
- "17/02/85" → "1985-02-17"
- "17.02.1985" → "1985-02-17"
- "17 FEV 1985" → "1985-02-17"

FORMATO DE SAÍDA (sempre YYYY-MM-DD):
{{"valor": "1985-02-17", "fonte": "arquivo.jpg", "confianca": 0.95}}

VALIDAÇÃO OBRIGATÓRIA:
- Formato deve ser YYYY-MM-DD
- Mês deve estar entre 01 e 12
- Dia deve estar entre 01 e 31
- Se não encontrar a data, use null mas com confiança 0.0


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
- Se não encontrar o CPF, use null mas com confiança 0.0


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
        "requisicao_entrada": "código se encontrado"
    }}
}}


 INSTRUÇÕES FINAIS


1. Se não conseguir ler um campo, use null no "valor" mas mantenha "fonte" e "confianca"
2. Score de confiança: 1.0 = perfeito, 0.5 = duvidoso, 0.0 = não encontrado
3. Retorne APENAS JSON válido, SEM markdown, SEM comentários, SEM ```json
4. Em caso de dúvida entre interpretações, escolha a mais literal (o que está escrito)
5. NUNCA invente dados - se não vê claramente, melhor deixar null

ANALISE A IMAGEM AGORA E EXTRAIA OS DADOS COM MÁXIMA PRECISÃO!
"""

        # Gerar resposta
        print("[OCR] Enviando para Vertex AI...")
        response = model.generate_content([prompt, image_part])

        # Extrair texto da resposta
        texto_resposta = response.text.strip()
        print(f"[OCR] Resposta do Vertex AI (primeiros 500 chars): {texto_resposta[:500]}...")

        # Salvar resposta completa em arquivo de debug
        try:
            debug_path = os.path.join(TEMP_IMAGES_DIR, f"debug_ocr_{imagem_nome}.json")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(texto_resposta)
            print(f"[OCR]  Resposta completa salva em: {debug_path}")
        except Exception as e:
            print(f"[OCR] Aviso: Não foi possível salvar debug: {e}")

        # Limpar possíveis markdown do JSON
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta.replace("```json", "").replace("```", "").strip()
        elif texto_resposta.startswith("```"):
            texto_resposta = texto_resposta.replace("```", "").strip()

        # Parse do JSON
        try:
            dados_extraidos = json.loads(texto_resposta)
            print(f"[OCR]  Dados extraídos com sucesso")
            print(f"[OCR]  DEBUG - tipo_documento: {dados_extraidos.get('tipo_documento')}")
            print(f"[OCR]  DEBUG - itens_exame RAW: {dados_extraidos.get('requisicao', {}).get('itens_exame')}")

            # LOG DETALHADO DOS DADOS DO PACIENTE
            if 'paciente' in dados_extraidos:
                print(f"[OCR]  DADOS DO PACIENTE EXTRAÍDOS ")
                paciente = dados_extraidos['paciente']

                # Nome
                nome = paciente.get('NomPaciente', {}).get('valor') if isinstance(paciente.get('NomPaciente'), dict) else paciente.get('NomPaciente')
                print(f"[OCR]    Nome: {nome}")

                # Data de Nascimento
                data_nasc = paciente.get('DtaNasc', {}).get('valor') if isinstance(paciente.get('DtaNasc'), dict) else paciente.get('DtaNasc')
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

        return jsonify({
            "sucesso": 1,
            "mensagem": "OCR processado com sucesso (português corrigido)",
            "dados": dados_extraidos,
            "debug_resposta_gemini": texto_resposta[:500]  # Primeiros 500 chars para debug
        }), 200

    except Exception as e:
        print(f"[OCR] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
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
        model = GenerativeModel("gemini-1.5-flash")

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
    'BIOPSIA': 1,  # Genérico = SOE
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

            # Mesclar dados do paciente - INCLUIR TODOS OS CAMPOS (dict, bool, str, number, null, list)
            if 'paciente' in dados_ocr and isinstance(dados_ocr['paciente'], dict):
                for key, value in dados_ocr['paciente'].items():
                    # Aceitar qualquer tipo: dict, bool, str, int, float, list, None
                    resultado_consolidado["requisicoes"][0]["paciente"][key] = value

            # Mesclar dados do médico - INCLUIR TODOS OS CAMPOS
            if 'medico' in dados_ocr and isinstance(dados_ocr['medico'], dict):
                for key, value in dados_ocr['medico'].items():
                    resultado_consolidado["requisicoes"][0]["medico"][key] = value

            # Mesclar dados do convênio - INCLUIR TODOS OS CAMPOS (inclusive booleanos true/false)
            if 'convenio' in dados_ocr and isinstance(dados_ocr['convenio'], dict):
                for key, value in dados_ocr['convenio'].items():
                    resultado_consolidado["requisicoes"][0]["convenio"][key] = value

            # Mesclar dados da requisição - INCLUIR TODOS OS CAMPOS (dict, list, str, etc)
            if 'requisicao' in dados_ocr and isinstance(dados_ocr['requisicao'], dict):
                tipo_doc = dados_ocr.get('tipo_documento', '')

                for key, value in dados_ocr['requisicao'].items():
                    # Para itens_exame, APENAS adicionar se for de um pedido médico
                    if key == 'itens_exame' and isinstance(value, list):
                        # Só adicionar exames de documentos tipo "pedido_medico"
                        if tipo_doc == 'pedido_medico' and len(value) > 0:
                            if key not in resultado_consolidado["requisicoes"][0]["requisicao"]:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key] = []

                            # Adicionar apenas se ainda não tiver exames (evitar duplicatas de múltiplos pedidos)
                            if len(resultado_consolidado["requisicoes"][0]["requisicao"][key]) == 0:
                                resultado_consolidado["requisicoes"][0]["requisicao"][key].extend(value)
                                print(f"[CONSOLIDAR]  Adicionados {len(value)} exames do pedido médico: {imagem_nome}")
                            else:
                                print(f"[CONSOLIDAR]  Ignorando exames duplicados da imagem: {imagem_nome}")
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
            print("[CONSOLIDAR] Adicionando dados da API ao resultado consolidado...")
            print(f"[CONSOLIDAR] Tipo de dados_api: {type(dados_api)}")
            print(f"[CONSOLIDAR] Conteúdo de dados_api: {dados_api}")

            # Verificar se dados_api é um dicionário válido
            if not isinstance(dados_api, dict):
                print(f"[CONSOLIDAR] ERRO: dados_api não é um dicionário, é {type(dados_api)}")
                dados_api = {}  # Usar dicionário vazio para evitar erro

            # Se não há resultados OCR, adicionar alerta
            if len(resultados_ocr) == 0:
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["alertas_processamento"] = "Dados extraídos apenas da API/Banco de Dados - Sem imagens para processar OCR"
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["arquivos_analisados"] = ["Nenhuma imagem processada"]
                resultado_consolidado["requisicoes"][0]["comentarios_gerais"]["documentos_identificados"] = [{
                    "id_documento": "api_db",
                    "tipo_documento": "banco_dados",
                    "descricao": "Dados carregados do banco de dados MySQL (sem OCR)"
                }]

            # Dados do Paciente da API
            if 'paciente' in dados_api:
                pac_api = dados_api['paciente']
                campos_paciente = {
                    'NomPaciente': pac_api.get('nome'),
                    'DtaNascimento': pac_api.get('dtaNasc'),
                    'sexo': pac_api.get('sexo'),
                    'cpf': pac_api.get('cpf'),
                    'RGNumero': pac_api.get('rg'),
                    'telCelular': pac_api.get('telCelular')
                }

                for campo, valor in campos_paciente.items():
                    # Só adicionar se não existe no OCR e se o valor não é None
                    if campo not in resultado_consolidado["requisicoes"][0]["paciente"] and valor:
                        resultado_consolidado["requisicoes"][0]["paciente"][campo] = {
                            "valor": valor,
                            "fonte": "API/Banco de Dados",
                            "confianca": 1.0
                        }

                # Endereço do paciente
                if 'endereco' in pac_api and pac_api['endereco']:
                    end = pac_api['endereco']
                    if 'endereco' not in resultado_consolidado["requisicoes"][0]["paciente"]:
                        resultado_consolidado["requisicoes"][0]["paciente"]['endereco'] = {}

                    campos_endereco = {
                        'cep': end.get('cep'),
                        'logradouro': end.get('logradouro'),
                        'numEndereco': end.get('numEndereco'),
                        'bairro': end.get('bairro'),
                        'cidade': end.get('cidade'),
                        'uf': end.get('uf')
                    }

                    for campo, valor in campos_endereco.items():
                        if valor:
                            resultado_consolidado["requisicoes"][0]["paciente"]['endereco'][campo] = {
                                "valor": valor,
                                "fonte": "API/Banco de Dados",
                                "confianca": 1.0
                            }

            # Dados do Médico da API
            if 'medico' in dados_api:
                med_api = dados_api['medico']
                campos_medico = {
                    'NomMedico': med_api.get('nome'),
                    'numConselho': med_api.get('crm'),
                    'ufConselho': med_api.get('uf'),
                    'tipoConselho': 'CRM'
                }

                for campo, valor in campos_medico.items():
                    if campo not in resultado_consolidado["requisicoes"][0]["medico"] and valor:
                        resultado_consolidado["requisicoes"][0]["medico"][campo] = {
                            "valor": valor,
                            "fonte": "API/Banco de Dados",
                            "confianca": 1.0
                        }

            # Dados da Requisição da API
            if 'requisicao' in dados_api:
                req_api = dados_api['requisicao']
                campos_requisicao = {
                    'dtaColeta': req_api.get('dtaColeta'),
                    'dadosClinicos': req_api.get('dadosClinicos'),
                    'numGuia': req_api.get('numGuia')
                }

                for campo, valor in campos_requisicao.items():
                    if campo not in resultado_consolidado["requisicoes"][0]["requisicao"] and valor:
                        resultado_consolidado["requisicoes"][0]["requisicao"][campo] = {
                            "valor": valor,
                            "fonte": "API/Banco de Dados",
                            "confianca": 1.0
                        }

        # LOG FINAL - Mostrar resumo do que foi consolidado
        print(f"\n[CONSOLIDAR] ===== RESUMO DA CONSOLIDAÇÃO =====")
        print(f"[CONSOLIDAR] Total de imagens processadas: {len(resultados_ocr)}")
        print(f"[CONSOLIDAR] Dados da API incluídos: {bool(dados_api)}")
        print(f"[CONSOLIDAR] Campos no paciente: {len(resultado_consolidado['requisicoes'][0]['paciente'])}")
        print(f"[CONSOLIDAR] Campos no medico: {len(resultado_consolidado['requisicoes'][0]['medico'])}")
        print(f"[CONSOLIDAR] Campos no convenio: {len(resultado_consolidado['requisicoes'][0]['convenio'])}")
        print(f"[CONSOLIDAR] Campos na requisicao: {len(resultado_consolidado['requisicoes'][0]['requisicao'])}")
        print(f"[CONSOLIDAR] =====================================\n")

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
    logger.info("")
    logger.info("METODOLOGIA ATUALIZADA:")
    logger.info("  - Usando fazer_requisicao_aplis() para todas as chamadas ao apLIS")
    logger.info("  - Suporte a requisicaoListar para listagem de requisições")
    logger.info("  - Logging detalhado de todas as requisições e respostas")
    logger.info("")
    logger.info("CORS configurado para aceitar requisicoes de qualquer origem")
    logger.info("URLs dinamicas habilitadas (funciona com localhost e ngrok)")
    logger.info("Logging completo habilitado (console + arquivo)")
    logger.info("=" * 80)
    logger.info("")
    logger.info("AGUARDANDO REQUISICOES...")
    logger.info("")

    app.run(debug=True, host='0.0.0.0', port=5000)
