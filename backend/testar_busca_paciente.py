"""
Script de teste para a busca de pacientes por CPF ou Nome Completo
"""
import requests
import json

# URL da API
API_URL = "http://localhost:5000/api/buscar-paciente"

def testar_busca_por_nome():
    """Testa busca por nome completo"""
    print("\n" + "="*80)
    print("🧪 TESTE 1: Busca por Nome Completo")
    print("="*80)
    
    dados = {
        "nome": "kaua larsson lopes de sousa"
    }
    
    print(f"📤 Enviando requisição: {dados}")
    
    try:
        response = requests.post(API_URL, json=dados, headers={'Content-Type': 'application/json'})
        
        print(f"\n📡 Status: {response.status_code}")
        
        resultado = response.json()
        print(f"\n📦 Resposta:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        if resultado.get('sucesso') == 1:
            paciente = resultado.get('paciente', {})
            print(f"\n✅ SUCESSO!")
            print(f"   ID Paciente: {paciente.get('idPaciente')}")
            print(f"   Nome: {paciente.get('nome')}")
            print(f"   CPF: {paciente.get('cpf')}")
            print(f"   Data Nascimento: {paciente.get('dataNascimento')}")
        else:
            print(f"\n❌ ERRO: {resultado.get('erro')}")
            
    except Exception as e:
        print(f"\n❌ Exceção: {e}")


def testar_busca_por_cpf():
    """Testa busca por CPF"""
    print("\n" + "="*80)
    print("🧪 TESTE 2: Busca por CPF")
    print("="*80)
    
    # Use um CPF válido do seu banco
    dados = {
        "cpf": "12345678900"  # Substitua por um CPF real do banco
    }
    
    print(f"📤 Enviando requisição: {dados}")
    
    try:
        response = requests.post(API_URL, json=dados, headers={'Content-Type': 'application/json'})
        
        print(f"\n📡 Status: {response.status_code}")
        
        resultado = response.json()
        print(f"\n📦 Resposta:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        if resultado.get('sucesso') == 1:
            paciente = resultado.get('paciente', {})
            print(f"\n✅ SUCESSO!")
            print(f"   ID Paciente: {paciente.get('idPaciente')}")
            print(f"   Nome: {paciente.get('nome')}")
            print(f"   CPF: {paciente.get('cpf')}")
            print(f"   Data Nascimento: {paciente.get('dataNascimento')}")
        else:
            print(f"\n❌ ERRO: {resultado.get('erro')}")
            
    except Exception as e:
        print(f"\n❌ Exceção: {e}")


def testar_busca_sem_parametros():
    """Testa busca sem parâmetros (deve falhar)"""
    print("\n" + "="*80)
    print("🧪 TESTE 3: Busca sem parâmetros (deve retornar erro)")
    print("="*80)
    
    dados = {}
    
    print(f"📤 Enviando requisição: {dados}")
    
    try:
        response = requests.post(API_URL, json=dados, headers={'Content-Type': 'application/json'})
        
        print(f"\n📡 Status: {response.status_code}")
        
        resultado = response.json()
        print(f"\n📦 Resposta:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        if response.status_code == 400:
            print(f"\n✅ Erro esperado retornado corretamente!")
        else:
            print(f"\n⚠️ Status inesperado: esperava 400, recebeu {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Exceção: {e}")


if __name__ == "__main__":
    print("\n🚀 INICIANDO TESTES DE BUSCA DE PACIENTES")
    print("Certifique-se de que a API está rodando em http://localhost:5000")
    
    # Executar testes
    testar_busca_por_nome()
    testar_busca_por_cpf()
    testar_busca_sem_parametros()
    
    print("\n" + "="*80)
    print("✅ TESTES CONCLUÍDOS")
    print("="*80)
    print("\nDicas:")
    print("  1. Ajuste o nome no TESTE 1 para um nome real do seu banco")
    print("  2. Ajuste o CPF no TESTE 2 para um CPF real do seu banco")
    print("  3. A busca por nome NÃO é case-sensitive (aceita maiúsculas/minúsculas)")
    print("")
