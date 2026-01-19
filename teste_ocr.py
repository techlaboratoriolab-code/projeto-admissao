#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para processar OCR de imagens da AWS
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import requests
import json

def testar_ocr_requisicao(cod_requisicao):
    """Testa o processamento OCR de uma requisição"""

    print(f"\n{'='*60}")
    print(f"TESTANDO OCR DA REQUISICAO: {cod_requisicao}")
    print(f"{'='*60}\n")

    url = "http://localhost:5000/api/ocr/processar"
    payload = {"cod_requisicao": cod_requisicao}

    print(f"Enviando requisicao para: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")

    try:
        response = requests.post(url, json=payload, timeout=180)

        print(f"Status Code: {response.status_code}\n")

        if response.status_code == 200:
            data = response.json()

            print(f"Sucesso: {data.get('sucesso')}")
            print(f"Total de requisicoes: {data.get('total_requisicoes')}")
            print(f"Total de imagens: {data.get('total_imagens_processadas')}\n")

            # Verificar se tem dados do paciente
            if data.get('requisicoes'):
                req = data['requisicoes'][0]

                if 'paciente' in req:
                    print(f"\n{'='*60}")
                    print(f"DADOS DO PACIENTE EXTRAIDOS")
                    print(f"{'='*60}\n")

                    paciente = req['paciente']

                    # Nome
                    nome = paciente.get('NomPaciente', {})
                    print(f"Nome: {nome.get('valor', 'N/A')}")
                    print(f"  Confianca: {nome.get('confianca', 'N/A')}")

                    # Data de Nascimento
                    data_nasc = paciente.get('DtaNasc', {})
                    print(f"\nData Nascimento: {data_nasc.get('valor', 'N/A')}")
                    print(f"  Confianca: {data_nasc.get('confianca', 'N/A')}")

                    # CPF
                    cpf = paciente.get('NumCPF', {})
                    print(f"\nCPF: {cpf.get('valor', 'N/A')}")
                    print(f"  Confianca: {cpf.get('confianca', 'N/A')}")

                    # RG
                    rg = paciente.get('NumRG', {})
                    print(f"\nRG: {rg.get('valor', 'N/A')}")
                    print(f"  Confianca: {rg.get('confianca', 'N/A')}")

                    # Telefone
                    tel = paciente.get('TelCelular', {})
                    print(f"\nTelefone: {tel.get('valor', 'N/A')}")
                    print(f"  Confianca: {tel.get('confianca', 'N/A')}")

                    # Endereco
                    end = paciente.get('DscEndereco', {})
                    print(f"\nEndereco: {end.get('valor', 'N/A')}")
                    print(f"  Confianca: {end.get('confianca', 'N/A')}")

                    print(f"\n{'='*60}\n")

                    # Salvar resultado completo
                    output_file = f"resultado_ocr_{cod_requisicao}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"Resultado completo salvo em: {output_file}")

                else:
                    print("AVISO: Nenhum dado de paciente encontrado na resposta!")
                    print(f"\nResposta completa:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print("AVISO: Nenhuma requisicao encontrada na resposta!")

        else:
            print(f"ERRO: {response.status_code}")
            print(f"Resposta: {response.text}")

    except requests.exceptions.Timeout:
        print("TIMEOUT: A requisicao demorou mais de 3 minutos")
    except Exception as e:
        print(f"ERRO ao processar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cod_req = sys.argv[1]
    else:
        cod_req = "85075411005"

    testar_ocr_requisicao(cod_req)
