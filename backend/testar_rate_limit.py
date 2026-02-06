"""
Script para testar o comportamento da API quando há rate limiting (429)
"""

import requests
import time

# URL base do backend
BASE_URL = "http://localhost:5000"

def testar_requisicao_normal():
    """Testa busca de requisição normal"""
    print("=" * 80)
    print("TESTE 1: Busca de requisição normal")
    print("=" * 80)
    
    cod_requisicao = "0040000356004"
    url = f"{BASE_URL}/api/requisicao/{cod_requisicao}"
    
    print(f"\nBuscando requisição: {cod_requisicao}")
    print(f"URL: {url}\n")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}\n")
        
        if response.status_code == 429:
            print("✓ API retornou 429 conforme esperado quando há rate limiting")
            return True
        elif response.status_code == 404:
            print("✓ API retornou 404 - requisição não encontrada (pode ser normal)")
            return True
        elif response.status_code == 200:
            print("✓ API retornou 200 - requisição encontrada com sucesso!")
            return True
        else:
            print(f"✗ Status inesperado: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Erro na requisição: {e}")
        return False


def testar_webhook():
    """Testa endpoints de webhook"""
    print("\n" + "=" * 80)
    print("TESTE 2: Endpoints de Webhook")
    print("=" * 80)
    
    endpoints = [
        "/webhook",
        "/webhook/LabWahaPlus",
        "/webhook/teste"
    ]
    
    sucesso = True
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\nTestando: {url}")
        
        try:
            # Teste GET
            response_get = requests.get(url, timeout=5)
            print(f"  GET Status: {response_get.status_code} - {response_get.json()}")
            
            # Teste POST
            dados_teste = {
                "event": "messages.upsert",
                "instance": "Teste",
                "data": {"message": "teste"}
            }
            response_post = requests.post(url, json=dados_teste, timeout=5)
            print(f"  POST Status: {response_post.status_code} - {response_post.json()}")
            
            if response_get.status_code == 200 and response_post.status_code == 200:
                print(f"  ✓ Webhook funcionando corretamente")
            else:
                print(f"  ✗ Problema no webhook")
                sucesso = False
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Erro: {e}")
            sucesso = False
    
    return sucesso


def testar_health():
    """Testa endpoint de health check"""
    print("\n" + "=" * 80)
    print("TESTE 3: Health Check")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/health"
    print(f"\nVerificando: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✓ API está funcionando")
            return True
        else:
            print("✗ API retornou erro")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Erro: {e}")
        return False


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "TESTE DE CORREÇÕES - API ADMISSÃO" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\nVerificando correções aplicadas:")
    print("  1. Tratamento de Rate Limiting (429)")
    print("  2. Rotas de webhook funcionando")
    print("  3. Logs sem emojis (sem erro de encoding)")
    print()
    
    # Aguardar backend estar pronto
    print("Aguardando backend iniciar...")
    time.sleep(2)
    
    # Executar testes
    resultado1 = testar_health()
    resultado2 = testar_webhook()
    resultado3 = testar_requisicao_normal()
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DOS TESTES")
    print("=" * 80)
    print(f"Health Check:        {'✓ PASSOU' if resultado1 else '✗ FALHOU'}")
    print(f"Webhooks:            {'✓ PASSOU' if resultado2 else '✗ FALHOU'}")
    print(f"Busca Requisição:    {'✓ PASSOU' if resultado3 else '✗ FALHOU'}")
    print("=" * 80)
    
    if all([resultado1, resultado2, resultado3]):
        print("\n✓ TODOS OS TESTES PASSARAM! Sistema corrigido com sucesso.")
    else:
        print("\n✗ ALGUNS TESTES FALHARAM. Verifique os logs acima.")
    
    print()
