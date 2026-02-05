"""
Script para investigar TODOS os métodos da API apLIS
e descobrir qual retorna os dados de convenio/local/fonte
"""
import requests
import json
import os
from dotenv import load_dotenv

# Credenciais do apLIS (do codigo backend)
APLIS_API_URL = "https://lab.aplis.inf.br/api/integracao.php"
APLIS_USER = "api.lab"
APLIS_PASS = "nintendo64"

print("=" * 80)
print("INVESTIGACAO: METODOS DA API apLIS")
print("=" * 80)

# Código de uma requisição para testar
COD_REQUISICAO = "0085075411005"

# ============================================================================
# TESTE 1: requisicaoStatus
# ============================================================================
print("\n[1] TESTANDO: requisicaoStatus")
print("-" * 80)

payload_status = {
    "ver": 2,
    "cmd": "requisicaoStatus",
    "dat": {
        "codRequisicao": COD_REQUISICAO
    }
}

try:
    response = requests.post(
        APLIS_API_URL,
        json=payload_status,
        auth=(APLIS_USER, APLIS_PASS)
    )

    if response.status_code == 200:
        data = response.json()
        print("Status Code: 200")
        print("\nCampos retornados:")
        if 'dat' in data:
            for key in data['dat'].keys():
                print(f"  - {key}")

            # Verificar se tem os campos que procuramos
            dat = data['dat']
            tem_convenio = 'convenio' in str(dat).lower()
            tem_local = 'local' in str(dat).lower()
            tem_fonte = 'fonte' in str(dat).lower()

            print(f"\nContem 'convenio': {tem_convenio}")
            print(f"Contem 'local': {tem_local}")
            print(f"Contem 'fonte': {tem_fonte}")
    else:
        print(f"Erro: {response.status_code}")
except Exception as e:
    print(f"ERRO: {e}")

# ============================================================================
# TESTE 2: requisicaoResultado
# ============================================================================
print("\n\n[2] TESTANDO: requisicaoResultado")
print("-" * 80)

payload_resultado = {
    "ver": 2,
    "cmd": "requisicaoResultado",
    "dat": {
        "codRequisicao": COD_REQUISICAO
    }
}

try:
    response = requests.post(
        APLIS_API_URL,
        json=payload_resultado,
        auth=(APLIS_USER, APLIS_PASS)
    )

    if response.status_code == 200:
        data = response.json()
        print("Status Code: 200")

        if 'dat' in data:
            dat = data['dat']
            print(f"\nSucesso: {dat.get('sucesso')}")

            # Verificar campos importantes
            if 'localOrigem' in dat:
                print(f"\n[ENCONTRADO] localOrigem:")
                print(f"  {json.dumps(dat['localOrigem'], indent=2, ensure_ascii=False)}")

            if 'convenio' in dat:
                print(f"\n[ENCONTRADO] convenio:")
                print(f"  {dat['convenio']}")

            # Mostrar todos os campos
            print(f"\nTODOS os campos retornados:")
            for key in dat.keys():
                if key not in ['paciente', 'procedimentos', 'topografias', 'guiaPrincipal']:
                    print(f"  - {key}: {type(dat[key]).__name__}")
    else:
        print(f"Erro: {response.status_code}")
        print(response.text[:500])
except Exception as e:
    print(f"ERRO: {e}")

# ============================================================================
# TESTE 3: requisicaoListar com MAIS DETALHES
# ============================================================================
print("\n\n[3] TESTANDO: requisicaoListar (usuarios internos)")
print("-" * 80)

payload_listar = {
    "ver": 2,
    "cmd": "requisicaoListar",
    "dat": {
        "tipoData": 1,
        "periodoIni": "2026-01-20",
        "periodoFim": "2026-01-22",
        "codRequisicao": COD_REQUISICAO,
        "pagina": 1,
        "tamanho": 1
    }
}

try:
    response = requests.post(
        APLIS_API_URL,
        json=payload_listar,
        auth=(APLIS_USER, APLIS_PASS)
    )

    if response.status_code == 200:
        data = response.json()
        print("Status Code: 200")

        if 'dat' in data and 'lista' in data['dat']:
            lista = data['dat']['lista']
            if lista:
                req = lista[0]
                print(f"\nRegistro encontrado: {req.get('CodRequisicao')}")

                # Mostrar TODOS os campos
                print(f"\nTODOS os campos do requisicaoListar:")
                for key, value in req.items():
                    tipo = type(value).__name__
                    valor_str = str(value)[:50] if value else 'None'
                    print(f"  - {key:25s} ({tipo:10s}): {valor_str}")

                # Verificar especificamente os IDs
                print(f"\n[VERIFICACAO] IDs importantes:")
                print(f"  IdConvenio: {req.get('IdConvenio')}")
                print(f"  IdLocalOrigem: {req.get('IdLocalOrigem')}")
                print(f"  IdFontePagadora: {req.get('IdFontePagadora')}")
                print(f"  NomeConvenio: {req.get('NomeConvenio')}")
                print(f"  NomeFontePagadora: {req.get('NomeFontePagadora')}")
                print(f"  NomeLocalOrigem: {req.get('NomeLocalOrigem')}")
    else:
        print(f"Erro: {response.status_code}")
except Exception as e:
    print(f"ERRO: {e}")

print("\n" + "=" * 80)
print("INVESTIGACAO CONCLUIDA")
print("=" * 80)
