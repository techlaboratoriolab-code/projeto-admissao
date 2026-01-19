#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar conexão com o banco de dados MySQL
"""

import mysql.connector
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv('backend/.env')

print("=" * 80)
print("TESTE DE CONEXÃO COM BANCO DE DADOS MYSQL")
print("=" * 80)
print()

# Mostrar configurações (sem mostrar senha completa)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'SENHA@ROOT')
DB_NAME = os.getenv('DB_NAME', 'bancodedados')

print("Configurações carregadas:")
print(f"  Host: {DB_HOST}")
print(f"  Usuário: {DB_USER}")
print(f"  Senha: {'*' * len(DB_PASSWORD) if DB_PASSWORD else 'NÃO DEFINIDA'}")
print(f"  Database: {DB_NAME}")
print()

# Testar conexão
print("Testando conexão com o banco de dados...")
print()

try:
    # Tentativa 1: Conectar sem especificar o banco de dados
    print("[Teste 1] Tentando conectar ao MySQL (sem especificar database)...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    print("  ✓ Conexão com MySQL estabelecida com sucesso!")

    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES;")
    databases = cursor.fetchall()

    print("\n  Databases disponíveis:")
    for db in databases:
        print(f"    - {db[0]}")

    # Verificar se o banco especificado existe
    db_existe = any(DB_NAME.lower() == db[0].lower() for db in databases)

    cursor.close()
    conn.close()

    print()

    if db_existe:
        print(f"  ✓ Database '{DB_NAME}' encontrado!")
        print()

        # Tentativa 2: Conectar ao banco específico
        print(f"[Teste 2] Tentando conectar ao database '{DB_NAME}'...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print(f"  ✓ Conectado ao database '{DB_NAME}' com sucesso!")

        # Listar tabelas
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tabelas = cursor.fetchall()

        if tabelas:
            print(f"\n  Tabelas encontradas ({len(tabelas)}):")
            for tabela in tabelas:
                print(f"    - {tabela[0]}")
        else:
            print(f"\n  ⚠ Database '{DB_NAME}' existe mas está vazio (sem tabelas).")

        cursor.close()
        conn.close()

        print()
        print("=" * 80)
        print("✓ CONEXÃO BEM-SUCEDIDA!")
        print("=" * 80)
        print("\nO banco de dados está configurado corretamente.")
        print("Se o erro persistir, verifique se o servidor MySQL está rodando.")

    else:
        print(f"  ✗ Database '{DB_NAME}' NÃO ENCONTRADO!")
        print()
        print("=" * 80)
        print("⚠ PROBLEMA IDENTIFICADO")
        print("=" * 80)
        print(f"\nO database '{DB_NAME}' não existe no MySQL.")
        print("\nSOLUÇÕES:")
        print(f"  1. Criar o database: CREATE DATABASE {DB_NAME};")
        print(f"  2. Ou usar um database existente alterando a variável DB_NAME no arquivo .env")

except mysql.connector.Error as err:
    print(f"  ✗ ERRO DE CONEXÃO!")
    print()
    print("=" * 80)
    print("DETALHES DO ERRO")
    print("=" * 80)

    if err.errno == 1045:
        print("\n❌ ERRO 1045: Acesso negado")
        print("\nProblema: Usuário ou senha incorretos")
        print("\nSOLUÇÕES:")
        print("  1. Verifique se a senha no arquivo .env está correta")
        print("  2. Teste a senha no MySQL Workbench ou outro cliente")
        print("  3. Redefina a senha do usuário root no MySQL:")
        print("     ALTER USER 'root'@'localhost' IDENTIFIED BY 'sua_nova_senha';")

    elif err.errno == 2003:
        print("\n❌ ERRO 2003: Não foi possível conectar ao servidor MySQL")
        print("\nProblema: Servidor MySQL não está rodando ou host incorreto")
        print("\nSOLUÇÕES:")
        print("  1. Verifique se o MySQL está rodando:")
        print("     - Abra 'Serviços' do Windows (services.msc)")
        print("     - Procure por 'MySQL' e verifique se está 'Em execução'")
        print("  2. Inicie o serviço MySQL se estiver parado")
        print("  3. Verifique se o host está correto (localhost ou 127.0.0.1)")

    elif err.errno == 1049:
        print(f"\n❌ ERRO 1049: Database '{DB_NAME}' não existe")
        print("\nProblema: O banco de dados especificado não foi encontrado")
        print("\nSOLUÇÕES:")
        print(f"  1. Criar o database: CREATE DATABASE {DB_NAME};")
        print(f"  2. Ou use um database existente alterando DB_NAME no .env")

    else:
        print(f"\n❌ Erro MySQL {err.errno}: {err.msg}")

    print(f"\nErro completo: {err}")

except Exception as e:
    print(f"  ✗ ERRO INESPERADO: {e}")
    import traceback
    traceback.print_exc()

print()
input("Pressione ENTER para sair...")
