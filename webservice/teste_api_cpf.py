"""
Script para testar a API de consulta de CPF
Hub do Desenvolvedor - Consulta CPF
"""

import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações da API - USAR VARIÁVEIS DE AMBIENTE
BASE_URL = os.getenv('HUB_DEV_BASE_URL', 'https://ws.hubdodesenvolvedor.com.br/v2/cpf/')
TOKEN = os.getenv('HUB_DEV_TOKEN', '')  # ⚠️ CONFIGURE NO .env

def consultar_cpf(cpf, data_nascimento):
    """
    Consulta CPF na API do Hub do Desenvolvedor

    Args:
        cpf: CPF no formato XXX.XXX.XXX-XX ou apenas números
        data_nascimento: Data de nascimento no formato DD/MM/YYYY

    Returns:
        dict: Dados retornados pela API
    """
    # Remove formatação do CPF (pontos e traços)
    cpf_limpo = cpf.replace(".", "").replace("-", "")

    # Monta a URL com os parâmetros
    url = f"{BASE_URL}?cpf={cpf_limpo}&data={data_nascimento}&token={TOKEN}"

    print(f"\n{'='*60}")
    print(f"Consultando CPF: {cpf}")
    print(f"Data de Nascimento: {data_nascimento}")
    print(f"URL: {url}")
    print(f"{'='*60}\n")

    try:
        # Faz a requisição
        response = requests.get(url, timeout=30)

        # Verifica o status da resposta
        print(f"Status Code: {response.status_code}")

        # Tenta decodificar o JSON
        resultado = response.json()

        # Exibe o resultado completo
        print("\nResposta completa da API:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

        # Verifica se a consulta foi bem-sucedida
        if resultado.get("return") == "OK":
            print("\n" + "="*60)
            print("CONSULTA BEM-SUCEDIDA!")
            print("="*60)

            result_data = resultado.get("result", {})

            print(f"\nNome: {result_data.get('nome_da_pf', 'N/A')}")
            print(f"CPF: {result_data.get('numero_de_cpf', 'N/A')}")
            print(f"Data de Nascimento: {result_data.get('data_nascimento', 'N/A')}")
            print(f"Situação Cadastral: {result_data.get('situacao_cadastral', 'N/A')}")
            print(f"Data Inscrição: {result_data.get('data_inscricao', 'N/A')}")
            print(f"Comprovante Emitido: {result_data.get('comprovante_emitido', 'N/A')}")
            print(f"Data do Comprovante: {result_data.get('comprovante_emitido_data', 'N/A')}")
            print(f"Dígito Verificador: {result_data.get('digito_verificador', 'N/A')}")

            return result_data
        else:
            print("\n" + "="*60)
            print("ERRO NA CONSULTA")
            print("="*60)
            print(f"Mensagem: {resultado.get('msg', 'Sem dados disponíveis')}")
            return None

    except requests.exceptions.Timeout:
        print("\nERRO: Timeout na requisição (tempo limite excedido)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\nERRO na requisição: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"\nERRO ao decodificar JSON: {e}")
        print(f"Resposta recebida: {response.text}")
        return None


def main():
    """Função principal para testar a API"""

    # Dados de teste fornecidos
    cpf_teste = "706.864.248-04"
    data_nascimento_teste = ""

    print("="*60)
    print("TESTE DA API DE CONSULTA DE CPF")
    print("Hub do Desenvolvedor")
    print("="*60)

    # Executa a consulta
    resultado = consultar_cpf(cpf_teste, data_nascimento_teste)

    if resultado:
        print("\n✓ Consulta realizada com sucesso!")
    else:
        print("\n✗ Falha na consulta")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
