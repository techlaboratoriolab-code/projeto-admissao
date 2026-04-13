#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrai médicos da tabela do banco de dados apLIS e salva em CSV para cache.
Colunas geradas: CodMedico, CRM, NomMedico, CRMUF
"""
import pymysql
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'newdb'),
    'charset': 'utf8mb4'
}


def extrair_medicos():
    """Extrai médicos do banco de dados e salva em CSV"""
    try:
        print("Conectando ao banco de dados...")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT
                CodMedico,
                CRM,
                NomMedico,
                CRMUF
            FROM newdb.cadmedico
            WHERE Inativo = 0
              AND NomMedico IS NOT NULL
              AND NomMedico != ''
            ORDER BY NomMedico ASC
        """

        print("Buscando médicos...")
        cursor.execute(query)
        medicos = cursor.fetchall()

        print(f"OK - {len(medicos)} médicos ativos encontrados")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'medicos_extraidos_{timestamp}.csv'
        pasta_dados = os.path.join(os.path.dirname(__file__), '..', 'dados')
        os.makedirs(pasta_dados, exist_ok=True)
        csv_path = os.path.join(pasta_dados, csv_filename)

        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            if medicos:
                writer = csv.DictWriter(f, fieldnames=['CodMedico', 'CRM', 'NomMedico', 'CRMUF'])
                writer.writeheader()
                writer.writerows(medicos)

        print(f"OK - Arquivo salvo: {csv_path}")

        print("\nPrimeiros 10 médicos:")
        for i, m in enumerate(medicos[:10], 1):
            print(f"  {i}. [{m['CodMedico']}] {m['NomMedico']} - CRM {m['CRM']}/{m['CRMUF']}")

        cursor.close()
        conn.close()

        return csv_filename

    except Exception as e:
        print(f"ERRO ao extrair médicos: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    print("=" * 60)
    print("EXTRAÇÃO DE MÉDICOS")
    print("=" * 60)
    resultado = extrair_medicos()
    print("=" * 60)
    if resultado:
        print(f"SUCESSO! Arquivo gerado: {resultado}")
        print("Atualize o nome do arquivo em api_admissao.py -> carregar_medicos_csv()")
    else:
        print("FALHA na extração de médicos")
    print("=" * 60)
