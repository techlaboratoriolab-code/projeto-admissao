"""
Script para testar o carregamento e busca no cache de instituições
"""

import os
import sys
import csv
from dotenv import load_dotenv

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(__file__))

# Carregar variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Cache global (simulando o do api_admissao.py)
INSTITUICOES_CACHE = {}

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
        print(f"❌ Nenhum arquivo de instituições encontrado em {pasta_dados}")
        return False
    
    # Usar o arquivo mais recente
    csv_path = sorted(arquivos_instituicoes)[-1]
    print(f"📂 Carregando: {os.path.basename(csv_path)}")

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_instituicao = row['IdInstituicao']
                INSTITUICOES_CACHE[id_instituicao] = {
                    'id': id_instituicao,
                    'nome': row['NomFantasia']
                }
        print(f"✅ {len(INSTITUICOES_CACHE)} instituições carregadas!")
        return True
    except Exception as e:
        print(f"❌ Erro ao carregar: {e}")
        import traceback
        traceback.print_exc()
        return False

def buscar_instituicao_por_nome(nome_busca):
    """Busca instituição no cache por nome com estratégia melhorada"""
    if not nome_busca or not isinstance(nome_busca, str):
        return None
        
    nome_busca_upper = nome_busca.upper().strip()
    
    # 1. Busca exata
    for id_inst, inst_data in INSTITUICOES_CACHE.items():
        nome_cache = inst_data.get('nome', '').upper()
        if nome_cache == nome_busca_upper:
            return inst_data
    
    # 2. Busca por palavra-chave (primeira palavra significativa)
    palavras = nome_busca_upper.split()
    palavra_chave = None
    for palavra in palavras:
        palavra_limpa = palavra.strip(',-()[]')
        if len(palavra_limpa) >= 3 and palavra_limpa not in ['DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'EM']:
            palavra_chave = palavra_limpa
            break
    
    if palavra_chave:
        print(f"   🔍 Palavra-chave: '{palavra_chave}'")
        for id_inst, inst_data in INSTITUICOES_CACHE.items():
            nome_cache = inst_data.get('nome', '').upper()
            if nome_cache.startswith(palavra_chave):
                return inst_data
    
    # 3. Busca parcial
    for id_inst, inst_data in INSTITUICOES_CACHE.items():
        nome_cache = inst_data.get('nome', '').upper()
        if nome_busca_upper in nome_cache or nome_cache in nome_busca_upper:
            return inst_data
    
    return None

def testar_buscas():
    """Testa várias buscas"""
    print("\n" + "="*60)
    print("🧪 TESTANDO BUSCAS")
    print("="*60)
    
    testes = [
        "CASSI",
        "CASSI - Caixa de Assistência dos Funcionários do Banco do Brasil",
        "AMIL",
        "UNIMED",
        "PARTICULAR",
        "INEXISTENTE XYZ"
    ]
    
    for i, nome_teste in enumerate(testes, 1):
        print(f"\n{i}. Buscando: '{nome_teste}'")
        resultado = buscar_instituicao_por_nome(nome_teste)
        if resultado:
            print(f"   ✅ ENCONTRADO: ID={resultado['id']}, Nome='{resultado['nome']}'")
        else:
            print(f"   ❌ NÃO ENCONTRADO")

if __name__ == "__main__":
    print("="*60)
    print("🧪 TESTE DO CACHE DE INSTITUIÇÕES")
    print("="*60)
    
    # Carregar cache
    if carregar_instituicoes_csv():
        # Mostrar amostra
        print(f"\n📋 Primeiras 10 instituições no cache:")
        for i, (id_inst, dados) in enumerate(list(INSTITUICOES_CACHE.items())[:10], 1):
            print(f"   {i}. ID={id_inst}: {dados['nome']}")
        
        # Testar buscas
        testar_buscas()
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ FALHA NO TESTE - Cache não carregado")
        print("="*60)
        print("\n💡 Execute: python backend/extrair_instituicoes.py")
