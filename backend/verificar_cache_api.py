"""
Script para verificar se o servidor backend está carregando o cache corretamente
"""

import requests
import json

API_BASE = "https://automacaolab.ngrok.dev"  # ou "http://localhost:5000"

def testar_cache_via_api():
    """Testa se a API está com o cache carregado"""
    print("="*60)
    print("🧪 TESTANDO CACHE VIA API REST")
    print("="*60)
    
    try:
        # Testar endpoint de instituições
        print("\n📡 GET /api/instituicoes")
        response = requests.get(f"{API_BASE}/api/instituicoes", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Total de instituições: {total}")
            
            if total > 0:
                instituicoes = data.get('instituicoes', [])
                print(f"\n📋 Primeiras 5 instituições:")
                for i, inst in enumerate(instituicoes[:5], 1):
                    print(f"   {i}. ID={inst['id']}: {inst['nome']}")
                return True
            else:
                print("❌ Cache vazio! Servidor precisa ser reiniciado.")
                return False
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar à API")
        print("   O servidor está rodando?")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    sucesso = testar_cache_via_api()
    
    print("\n" + "="*60)
    if sucesso:
        print("✅ CACHE CARREGADO - Sistema funcionando!")
    else:
        print("⚠️ CACHE NÃO CARREGADO")
        print("\n💡 SOLUÇÃO:")
        print("   1. Pare o servidor backend (Ctrl+C)")
        print("   2. Execute: iniciar_sistema.bat")
        print("   3. Aguarde carregar completamente")
    print("="*60)
