#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrai locais de origem da tabela fatinstituicao e salva em CSV
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

def extrair_locais_origem():
    """Extrai locais de origem da tabela fatinstituicao"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        print("Extraindo locais de origem da tabela fatinstituicao...")
        
        # Local = 1 identifica registros de fatinstituicao que são locais de origem
        # (clínicas/hospitais que enviam exames). Inativo = 0 garante apenas ativos.
        query = """
            SELECT
                IdInstituicao,
                NomFantasia
            FROM newdb.fatinstituicao
            WHERE Local = 1
              AND Inativo = 0
              AND NomFantasia IS NOT NULL
              AND NomFantasia != ''
            ORDER BY NomFantasia ASC
        """

        cursor.execute(query)
        locais = cursor.fetchall()

        # Nome do arquivo CSV com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'locais_origem_extraidos_{timestamp}.csv'
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'dados', csv_filename)

        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        # Salvar em CSV
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            if locais:
                writer = csv.DictWriter(f, fieldnames=['IdInstituicao', 'NomFantasia'])
                writer.writeheader()
                writer.writerows(locais)

        print(f"OK - {len(locais)} locais de origem ativos extraidos (Local=1, Inativo=0)")
        print(f"OK - Arquivo salvo: {csv_path}")
        
        cursor.close()
        conn.close()
        
        return csv_filename
        
    except Exception as e:
        print(f"ERRO ao extrair locais de origem: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    extrair_locais_origem()
