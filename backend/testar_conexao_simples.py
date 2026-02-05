"""
Teste rápido de conexão com o banco de dados
"""
import pymysql
import os
import sys
from dotenv import load_dotenv

# Configurar encoding UTF-8 para evitar erros com emojis
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Carregar variáveis de ambiente
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'SENHA@ROOT'),
    'database': os.getenv('DB_NAME', 'newdb'),
    'charset': 'utf8mb4'
}

print("Testando conexao com banco de dados...")
print(f"   Host: {DB_CONFIG['host']}")
print(f"   User: {DB_CONFIG['user']}")
print(f"   Database: {DB_CONFIG['database']}")
print()

try:
    connection = pymysql.connect(**DB_CONFIG)
    print("[OK] Conexão estabelecida com sucesso!")

    # Testar busca de paciente por CPF
    with connection.cursor() as cursor:
        cpf_teste = "86812378100"
        query = """
            SELECT CodPaciente, NomPaciente, CPF, DtaNascimento
            FROM newdb.paciente
            WHERE CPF = %s
        """

        print(f"\n Buscando paciente com CPF: {cpf_teste}")
        cursor.execute(query, (cpf_teste,))
        resultados = cursor.fetchall()

        if resultados:
            print(f"[OK] Encontrados {len(resultados)} registro(s):")
            for idx, reg in enumerate(resultados, 1):
                print(f"   {idx}. CodPaciente: {reg[0]}")
                print(f"      Nome: {reg[1]}")
                print(f"      CPF: {reg[2]}")
                print(f"      Data Nasc: {reg[3]}")
                print()
        else:
            print("[ERRO] Nenhum paciente encontrado com esse CPF")

    connection.close()
    print("[OK] Teste concluído com sucesso!")

except pymysql.Error as e:
    print(f"[ERRO] Erro de conexão MySQL: {e}")
    print(f"   Código do erro: {e.args[0]}")
    print(f"   Mensagem: {e.args[1] if len(e.args) > 1 else 'N/A'}")
except Exception as e:
    print(f"[ERRO] Erro inesperado: {e}")
