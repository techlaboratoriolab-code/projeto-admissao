"""
Script para descobrir a estrutura das tabelas do banco apLIS
"""

import pymysql
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configuração do banco
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'newdb'),
    'charset': 'utf8mb4'
}

def listar_tabelas():
    """Lista todas as tabelas do banco"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        print("🔍 Buscando tabelas no banco 'newdb'...")
        cursor.execute("SHOW TABLES")
        tabelas = cursor.fetchall()

        print(f"\n✅ Encontradas {len(tabelas)} tabelas:\n")
        
        for i, tabela in enumerate(tabelas, 1):
            nome_tabela = tabela[0]
            print(f"{i}. {nome_tabela}")
            
            # Se o nome contém "institu", "fonte", "pagad" ou "convenio", mostrar estrutura
            if any(palavra in nome_tabela.lower() for palavra in ['institu', 'fonte', 'pagad', 'convenio']):
                print(f"   📋 Estrutura da tabela {nome_tabela}:")
                cursor.execute(f"DESCRIBE {nome_tabela}")
                campos = cursor.fetchall()
                for campo in campos[:5]:  # Primeiros 5 campos
                    print(f"      - {campo[0]} ({campo[1]})")
                print()

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*60)
    print("🔍 DESCOBRINDO ESTRUTURA DO BANCO apLIS")
    print("="*60)
    listar_tabelas()
