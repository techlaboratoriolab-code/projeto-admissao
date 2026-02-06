"""
Script para extrair instituições (fontes pagadoras) do banco de dados apLIS
e salvar em CSV para cache
"""

import pymysql
import csv
import os
from datetime import datetime
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

def extrair_instituicoes():
    """Extrai instituições do banco de dados e salva em CSV"""
    try:
        print("🔄 Conectando ao banco de dados...")
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Buscar todas as instituições (fontes pagadoras)
        # Nota: fatinstituicao tem apenas IDs e códigos, precisamos juntar com outras tabelas
        query = """
            SELECT DISTINCT
                fi.IdInstituicao,
                COALESCE(fci.IdConvenio, 0) as IdConvenio,
                fc.NomConvenio as NomFantasia
            FROM newdb.fatinstituicao fi
            LEFT JOIN newdb.fatconvenioinstituicao fci ON fi.IdInstituicao = fci.IdInstituicao
            LEFT JOIN newdb.fatconvenio fc ON fci.IdConvenio = fc.IdConvenio
            WHERE fc.NomConvenio IS NOT NULL
            ORDER BY fc.NomConvenio
        """

        print("🔍 Buscando instituições...")
        cursor.execute(query)
        instituicoes = cursor.fetchall()

        print(f"✅ Encontradas {len(instituicoes)} instituições ativas")

        # Salvar em CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta_dados = os.path.join(os.path.dirname(__file__), '..', 'dados')
        os.makedirs(pasta_dados, exist_ok=True)
        
        arquivo_csv = os.path.join(pasta_dados, f'instituicoes_extraidas_{timestamp}.csv')

        print(f"💾 Salvando em {arquivo_csv}...")
        
        with open(arquivo_csv, 'w', newline='', encoding='utf-8-sig') as f:
            if instituicoes:
                fieldnames = ['IdInstituicao', 'IdConvenio', 'NomFantasia']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(instituicoes)

        print(f"✅ Arquivo CSV criado com sucesso!")
        print(f"📂 Localização: {arquivo_csv}")
        
        # Exibir primeiras 10 instituições
        print("\n📋 Primeiras 10 instituições:")
        for i, inst in enumerate(instituicoes[:10], 1):
            print(f"  {i}. ID: {inst['IdInstituicao']} - {inst['NomFantasia']}")

        cursor.close()
        connection.close()

        return arquivo_csv

    except Exception as e:
        print(f"❌ Erro ao extrair instituições: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("="*60)
    print("🏥 EXTRAÇÃO DE INSTITUIÇÕES (FONTES PAGADORAS)")
    print("="*60)
    arquivo = extrair_instituicoes()
    if arquivo:
        print("\n" + "="*60)
        print("✅ SUCESSO! Instituições extraídas com sucesso!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ FALHA na extração de instituições")
        print("="*60)
