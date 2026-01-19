"""
Script para testar diferentes padrões de caminho no S3
e encontrar onde as imagens realmente estão armazenadas
"""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações AWS S3
S3_CONFIG = {
    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
    'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
    'region_name': os.getenv('AWS_REGION', 'sa-east-1')
}
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'aplis2')

# Criar cliente S3
s3 = boto3.client('s3', **S3_CONFIG)

# Informações da imagem que estamos tentando encontrar
cod_requisicao = "0040000356004"
nome_arquivo = "0040000356004_1"
extensao = "png"

print("=" * 80)
print("TESTANDO DIFERENTES PADRÕES DE CAMINHO NO S3")
print("=" * 80)
print(f"Bucket: {S3_BUCKET}")
print(f"Requisição: {cod_requisicao}")
print(f"Arquivo: {nome_arquivo}.{extensao}")
print("\n")

# Lista de padrões para testar
padroes = [
    # Padrão atual (que está falhando)
    f"lab/Arquivos/Foto/0040/{nome_arquivo}.{extensao}",

    # Sem o prefixo 'lab'
    f"Arquivos/Foto/0040/{nome_arquivo}.{extensao}",

    # Só o nome do arquivo
    f"{nome_arquivo}.{extensao}",

    # Com código completo da requisição como pasta
    f"lab/Arquivos/Foto/{cod_requisicao}/{nome_arquivo}.{extensao}",
    f"Arquivos/Foto/{cod_requisicao}/{nome_arquivo}.{extensao}",

    # Variações com maiúsculas/minúsculas
    f"lab/arquivos/foto/0040/{nome_arquivo}.{extensao}",
    f"Lab/Arquivos/Foto/0040/{nome_arquivo}.{extensao}",

    # Extensão em maiúscula
    f"lab/Arquivos/Foto/0040/{nome_arquivo}.PNG",

    # Sem pasta intermediária
    f"lab/Foto/0040/{nome_arquivo}.{extensao}",

    # Caminho mais curto
    f"Foto/0040/{nome_arquivo}.{extensao}",

    # Apenas com prefixo do lab
    f"0040/{nome_arquivo}.{extensao}",
]

encontrados = []
nao_encontrados = []

for idx, caminho in enumerate(padroes, 1):
    print(f"[{idx}/{len(padroes)}] Testando: {caminho}")
    try:
        # Tentar fazer HEAD request para verificar se existe
        s3.head_object(Bucket=S3_BUCKET, Key=caminho)
        print(f"    [OK] ENCONTRADO!")
        encontrados.append(caminho)
    except s3.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"    [X] 404 - Nao encontrado")
            nao_encontrados.append(caminho)
        else:
            print(f"    [X] Erro: {error_code}")
    except Exception as e:
        print(f"    [X] Erro inesperado: {e}")

print("\n" + "=" * 80)
print("RESUMO DOS TESTES")
print("=" * 80)

if encontrados:
    print(f"\n[OK] ARQUIVOS ENCONTRADOS ({len(encontrados)}):")
    for caminho in encontrados:
        print(f"  - {caminho}")
else:
    print("\n[X] Nenhum arquivo encontrado com os padroes testados")

print(f"\n[X] Arquivos nao encontrados: {len(nao_encontrados)}")

# Tentar listar objetos com prefixos diferentes para descobrir a estrutura
print("\n" + "=" * 80)
print("TENTANDO LISTAR OBJETOS NO BUCKET COM DIFERENTES PREFIXOS")
print("=" * 80)

prefixos_para_listar = [
    "lab/",
    "Arquivos/",
    "lab/Arquivos/",
    "Foto/",
    "0040/",
    nome_arquivo[:10],  # Primeiros 10 caracteres do nome
]

for prefixo in prefixos_para_listar:
    print(f"\nListando com prefixo: '{prefixo}'")
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefixo,
            MaxKeys=10  # Apenas 10 para não sobrecarregar
        )

        if 'Contents' in response:
            print(f"  [OK] Encontrados {response['KeyCount']} objetos:")
            for obj in response['Contents'][:5]:  # Mostrar apenas os 5 primeiros
                print(f"    - {obj['Key']}")
            if response['KeyCount'] > 5:
                print(f"    ... e mais {response['KeyCount'] - 5} objetos")
        else:
            print("  [X] Nenhum objeto encontrado com este prefixo")
    except Exception as e:
        print(f"  [X] Erro ao listar: {e}")

print("\n" + "=" * 80)
