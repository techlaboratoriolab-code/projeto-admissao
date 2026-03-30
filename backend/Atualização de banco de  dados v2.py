import subprocess
import os
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import pymysql
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
import py7zr
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# ========== CONFIGURAÇÕES AWS S3 ==========
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'sa-east-1')
AWS_BUCKET = os.getenv('AWS_BUCKET', 'aplis2')
AWS_PREFIX = os.getenv('AWS_PREFIX', 'lab/DB/Diario/')

# ========== CONFIGURAÇÕES DE DOWNLOAD ==========
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', r'C:\Users\Windows 11\Desktop\saida-aws')
EXTRACTION_DIR = os.getenv('EXTRACTION_DIR', r'C:\Users\Windows 11\Desktop\saida-aws')
PASSWORD_7Z = os.getenv('PASSWORD_7Z', 'lab_00421')

# ========== CONFIGURAÇÕES SQL ==========
ARQUIVOS_SQL = [
    os.path.join(DOWNLOAD_DIR, 'lab1.bak'),
    os.path.join(DOWNLOAD_DIR, 'lab2.bak'),
    os.path.join(DOWNLOAD_DIR, 'lab3.bak'),
    os.path.join(DOWNLOAD_DIR, 'lab4.bak')
]

# ========== CONFIGURAÇÕES DE EXPORTAÇÃO CSV ==========
CAMINHO_ARQUIVO_TABELAS_TXT = os.getenv('CAMINHO_ARQUIVO_TABELAS_TXT', r'C:\Users\Windows 11\Downloads\sqltables.txt')
PASTA_SAIDA_CSV = os.getenv('PASTA_SAIDA_CSV', r'C:\Users\Windows 11\Desktop\lista')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'newdb')
}

# ========================================
# PARTE 1: FUNÇÕES AWS S3
# ========================================

def criar_cliente_s3():
    """Cria e retorna cliente boto3 para S3"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        print("[OK] Cliente S3 criado com sucesso")
        return s3_client
    except NoCredentialsError:
        print("[ERRO] Credenciais AWS não encontradas")
        return None
    except Exception as e:
        print(f"[ERRO] Erro ao criar cliente S3: {e}")
        return None

def listar_backups_s3(s3_client):
    """Lista todos os arquivos .7z no prefixo especificado"""
    try:
        print(f"\n{'='*80}")
        print(f"[S3] LISTANDO BACKUPS NO BUCKET")
        print(f"{'='*80}")
        print(f"Bucket: {AWS_BUCKET}")
        print(f"Prefixo: {AWS_PREFIX}")
        print(f"{'='*80}\n")

        response = s3_client.list_objects_v2(
            Bucket=AWS_BUCKET,
            Prefix=AWS_PREFIX
        )

        if 'Contents' not in response:
            print("[AVISO] Nenhum arquivo encontrado no bucket")
            return []

        # Filtra apenas arquivos .7z
        backups = [
            obj for obj in response['Contents']
            if obj['Key'].endswith('.7z')
        ]

        if not backups:
            print("[AVISO] Nenhum arquivo .7z encontrado")
            return []

        # Ordena por data de modificação (mais recente primeiro)
        backups_ordenados = sorted(
            backups,
            key=lambda x: x['LastModified'],
            reverse=True
        )

        print(f"[INFO] Encontrados {len(backups_ordenados)} backup(s):\n")
        for idx, backup in enumerate(backups_ordenados[:5], 1):  # Mostra top 5
            nome = os.path.basename(backup['Key'])
            data = backup['LastModified'].strftime("%Y-%m-%d %H:%M:%S")
            tamanho_mb = backup['Size'] / 1024 / 1024
            print(f"  {idx}. {nome}")
            print(f"     Data: {data}")
            print(f"     Tamanho: {tamanho_mb:.2f} MB\n")

        return backups_ordenados

    except ClientError as e:
        print(f"[ERRO] Erro ao listar objetos do S3: {e}")
        return []
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        return []

def baixar_backup_mais_recente(s3_client, backups):
    """Baixa o backup mais recente do S3"""
    if not backups:
        print("[ERRO] Nenhum backup disponível para download")
        return None

    backup_mais_recente = backups[0]
    key = backup_mais_recente['Key']
    nome_arquivo = os.path.basename(key)
    caminho_local = os.path.join(DOWNLOAD_DIR, nome_arquivo)

    # Cria diretório se não existir
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"[S3] BAIXANDO BACKUP MAIS RECENTE")
    print(f"{'='*80}")
    print(f"Arquivo: {nome_arquivo}")
    print(f"Data: {backup_mais_recente['LastModified'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tamanho: {backup_mais_recente['Size'] / 1024 / 1024:.2f} MB")
    print(f"Destino: {caminho_local}")
    print(f"{'='*80}\n")

    try:
        # Verifica se arquivo já existe
        if os.path.exists(caminho_local):
            resposta = input(f"Arquivo '{nome_arquivo}' já existe. Deseja baixar novamente? (S/N): ").strip().upper()
            if resposta not in ['S', 'SIM']:
                print("[INFO] Download cancelado. Usando arquivo existente.")
                return caminho_local

        print("[INFO] Iniciando download...")

        # Baixa com barra de progresso
        file_size = backup_mais_recente['Size']
        downloaded = 0

        def progress_callback(bytes_transferred):
            nonlocal downloaded
            downloaded += bytes_transferred
            percent = (downloaded / file_size) * 100
            print(f"\rProgresso: {percent:.1f}% ({downloaded / 1024 / 1024:.2f} MB / {file_size / 1024 / 1024:.2f} MB)", end='', flush=True)

        s3_client.download_file(
            AWS_BUCKET,
            key,
            caminho_local,
            Callback=progress_callback
        )

        print(f"\n\n[OK] Download concluído: {caminho_local}\n")
        return caminho_local

    except ClientError as e:
        print(f"\n[ERRO] Erro ao baixar arquivo: {e}")
        return None
    except Exception as e:
        print(f"\n[ERRO] Erro inesperado: {e}")
        return None

def extrair_arquivo_7z(caminho_arquivo, pasta_destino, senha):
    """Extrai arquivo .7z com senha"""
    if not os.path.exists(caminho_arquivo):
        print(f"[ERRO] Arquivo não encontrado: {caminho_arquivo}")
        return False

    print(f"\n{'='*80}")
    print(f"[7Z] EXTRAINDO ARQUIVO")
    print(f"{'='*80}")
    print(f"Arquivo: {os.path.basename(caminho_arquivo)}")
    print(f"Destino: {pasta_destino}")
    print(f"{'='*80}\n")

    try:
        os.makedirs(pasta_destino, exist_ok=True)

        with py7zr.SevenZipFile(caminho_arquivo, mode='r', password=senha) as archive:
            archive.extractall(path=pasta_destino)

        print(f"[OK] Extração concluída com sucesso!\n")

        # Lista arquivos extraídos
        arquivos_extraidos = [f for f in os.listdir(pasta_destino) if f.endswith('.bak')]
        if arquivos_extraidos:
            print(f"[INFO] Arquivos .bak extraídos:")
            for arquivo in arquivos_extraidos:
                tamanho_mb = os.path.getsize(os.path.join(pasta_destino, arquivo)) / 1024 / 1024
                print(f"  - {arquivo} ({tamanho_mb:.2f} MB)")
            print()

        return True

    except Exception as e:
        print(f"[ERRO] Erro ao extrair arquivo: {e}")
        return False

# ========================================
# PARTE 2: FUNÇÕES MYSQL (IMPORTAÇÃO)
# ========================================

def configurar_mysql_para_importacao(config):
    """Configura o MySQL para aceitar importação de dumps com funções"""
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password']
        )

        with connection.cursor() as cursor:
            cursor.execute("SET GLOBAL log_bin_trust_function_creators = 1;")

        connection.commit()
        connection.close()
        print("✓ MySQL configurado para aceitar importação de funções")
        return True

    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível configurar MySQL: {e}")
        print("A importação pode falhar se houver funções no dump.")
        return False

def testar_conexao_mysql(config):
    """Testa a conexão com o banco de dados MySQL"""
    try:
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        connection.close()
        print(f"✓ Conexão com MySQL bem-sucedida! (Host: {config['host']}, DB: {config['database']})")
        return True
    except pymysql.err.OperationalError as e:
        print(f"✗ Erro de conexão com MySQL: {e}")
        print(f"\nVerifique:")
        print(f"  1. MySQL está rodando? (Serviço: MySQL80)")
        print(f"  2. Host: {config['host']}")
        print(f"  3. Porta: {config['port']}")
        print(f"  4. Usuário: {config['user']}")
        print(f"  5. Senha está correta?")
        print(f"  6. Banco '{config['database']}' existe?")
        return False
    except Exception as e:
        print(f"✗ Erro inesperado ao testar conexão: {e}")
        return False

def importar_sql_para_mysql(caminho_arquivo_sql, db_config):
    """Importa um arquivo SQL (dump) para o banco de dados MySQL"""
    if not os.path.exists(caminho_arquivo_sql):
        print(f"[ERRO] Arquivo não encontrado: {caminho_arquivo_sql}")
        return False

    mysql_exe = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

    if not os.path.exists(mysql_exe):
        print(f"[ERRO] MySQL não encontrado em {mysql_exe}")
        print("Verifique se o MySQL está instalado ou ajuste o caminho no script.")
        return False

    try:
        tamanho_mb = os.path.getsize(caminho_arquivo_sql) / 1024 / 1024

        print(f"\n[IMPORT] Importando {os.path.basename(caminho_arquivo_sql)} ({tamanho_mb:.2f} MB)...")
        print(f"[INFO] Banco de dados: {db_config['database']}")

        command = [
            mysql_exe,
            f'--host={db_config["host"]}',
            f'--port={db_config["port"]}',
            f'--user={db_config["user"]}',
            f'--password={db_config["password"]}',
            f'--database={db_config["database"]}'
        ]

        with open(caminho_arquivo_sql, 'r', encoding='utf-8', errors='ignore') as f:
            process = subprocess.run(
                command,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos
            )

        if process.returncode == 0:
            print(f"[OK] {os.path.basename(caminho_arquivo_sql)} importado com sucesso!")
            return True
        else:
            print(f"[ERRO] Erro ao importar {caminho_arquivo_sql}")
            print(f"Código de retorno: {process.returncode}")
            if process.stderr:
                print(f"Erro: {process.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"[ERRO] Timeout ao importar {caminho_arquivo_sql}")
        print("O arquivo demorou mais de 30 minutos para ser importado.")
        return False
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        return False

# ========================================
# PARTE 3: FUNÇÕES CSV (EXPORTAÇÃO)
# ========================================

def ler_tabelas_do_arquivo(caminho_arquivo_txt):
    """Lê os nomes das tabelas de um arquivo TXT"""
    tabelas = []
    if not os.path.exists(caminho_arquivo_txt):
        print(f"[ERRO] Arquivo de tabelas não encontrado: {caminho_arquivo_txt}")
        return tabelas

    try:
        with open(caminho_arquivo_txt, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            content = content.strip('()[]{}')
            raw_tabelas = content.split(',')

            for item in raw_tabelas:
                clean_item = item.strip().strip('\'" ')
                if clean_item:
                    tabelas.append(clean_item)

        print(f"[INFO] Tabelas lidas: {', '.join(tabelas)}")
    except Exception as e:
        print(f"[ERRO] Erro ao ler arquivo de tabelas: {e}")

    return tabelas

def exportar_tabelas_especificas_para_csv(config, tabelas_para_exportar, pasta_saida):
    """Exporta tabelas específicas do MySQL para arquivos CSV"""
    user_encoded = quote_plus(config['user'])
    password_encoded = quote_plus(config['password'])

    db_connection_str = (
        f"mysql+pymysql://{user_encoded}:{password_encoded}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )

    try:
        engine = create_engine(db_connection_str)
    except Exception as e:
        print(f"[ERRO] Erro ao criar engine de conexão: {e}")
        return

    os.makedirs(pasta_saida, exist_ok=True)

    if not tabelas_para_exportar:
        print("[AVISO] Nenhuma tabela especificada para exportar")
        return

    try:
        with engine.connect() as connection:
            print(f"\n[CSV] Conectado ao banco '{config['database']}'")

            existing_tables_df = pd.read_sql("SHOW TABLES", connection)
            existing_tables = [row[0] for row in existing_tables_df.values]

            for tabela in tabelas_para_exportar:
                if tabela not in existing_tables:
                    print(f"[AVISO] Tabela '{tabela}' não encontrada. Pulando.")
                    continue

                print(f"[CSV] Exportando tabela {tabela}...")
                try:
                    df = pd.read_sql(f"SELECT * FROM `{tabela}`", connection)
                    arquivo_csv = os.path.join(pasta_saida, f"{tabela}.csv")
                    df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
                    print(f"[OK] Tabela {tabela} exportada para {arquivo_csv}")
                except Exception as e:
                    print(f"[ERRO] Erro ao exportar tabela {tabela}: {e}")

    except Exception as e:
        print(f"[ERRO] Erro geral durante exportação: {e}")
    finally:
        print("[INFO] Exportação de tabelas concluída")

# ========================================
# FUNÇÃO PRINCIPAL
# ========================================

def main():
    """Função principal - executa todo o fluxo"""

    print(f"\n{'='*80}")
    print(f"ATUALIZAÇÃO DE BANCO DE DADOS - AWS S3 + MYSQL")
    print(f"{'='*80}")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # ETAPA 1: Baixar backup mais recente do S3
    print("\n=== ETAPA 1: DOWNLOAD DO BACKUP MAIS RECENTE ===\n")

    s3_client = criar_cliente_s3()
    if not s3_client:
        print("[ERRO] Não foi possível criar cliente S3. Abortando.")
        return

    backups = listar_backups_s3(s3_client)
    if not backups:
        print("[ERRO] Nenhum backup encontrado. Abortando.")
        return

    caminho_backup = baixar_backup_mais_recente(s3_client, backups)
    if not caminho_backup:
        print("[ERRO] Falha no download. Abortando.")
        return

    # ETAPA 2: Extrair arquivo .7z
    print("\n=== ETAPA 2: EXTRAÇÃO DO BACKUP ===\n")

    if not extrair_arquivo_7z(caminho_backup, EXTRACTION_DIR, PASSWORD_7Z):
        print("[ERRO] Falha na extração. Abortando.")
        return

    # ETAPA 3: Configurar MySQL
    print("\n=== ETAPA 3: CONFIGURAÇÃO DO MYSQL ===\n")

    configurar_mysql_para_importacao(DB_CONFIG)

    # ETAPA 4: Importar arquivos SQL
    print("\n=== ETAPA 4: IMPORTAÇÃO DOS DUMPS SQL ===\n")

    arquivos_importados = 0
    for arquivo_sql in ARQUIVOS_SQL:
        if os.path.exists(arquivo_sql):
            if importar_sql_para_mysql(arquivo_sql, DB_CONFIG):
                arquivos_importados += 1
        else:
            print(f"[AVISO] Arquivo não encontrado: {arquivo_sql}")

    print(f"\n[RESUMO] {arquivos_importados}/{len(ARQUIVOS_SQL)} arquivo(s) importado(s)")

    if arquivos_importados == 0:
        print("[ERRO] Nenhum arquivo foi importado. Abortando exportação CSV.")
        return

    # ETAPA 5: Testar conexão MySQL
    print("\n=== ETAPA 5: TESTE DE CONEXÃO ===\n")

    if not testar_conexao_mysql(DB_CONFIG):
        print("[ERRO] Não foi possível conectar ao MySQL. Abortando exportação CSV.")
        return

    # ETAPA 6: Exportar tabelas para CSV
    print("\n=== ETAPA 6: EXPORTAÇÃO PARA CSV ===\n")

    tabelas_desejadas = ler_tabelas_do_arquivo(CAMINHO_ARQUIVO_TABELAS_TXT)

    if tabelas_desejadas:
        exportar_tabelas_especificas_para_csv(DB_CONFIG, tabelas_desejadas, PASTA_SAIDA_CSV)
    else:
        print("[AVISO] Nenhuma tabela para exportar")

    # aqui termina joão madeiro da silva bradesco junior
    print(f"\n{'='*80}")
    print(f"PROCESSO CONCLUÍDO COM SUCESSO!")
    print(f"{'='*80}")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()