import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'SENHA@ROOT',
    'database': 'bancodedados'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Listar todas as tabelas
    cursor.execute("SHOW TABLES")
    tabelas = cursor.fetchall()

    print("=" * 80)
    print("TABELAS NO BANCO 'bancodedados':")
    print("=" * 80)
    for tabela in tabelas:
        print(f"  - {tabela[0]}")

    print("\n" + "=" * 80)
    print("ESTRUTURA DA TABELA 'requisicao':")
    print("=" * 80)
    cursor.execute("DESCRIBE requisicao")
    colunas = cursor.fetchall()
    for col in colunas:
        print(f"  {col[0]} ({col[1]})")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Erro: {e}")
