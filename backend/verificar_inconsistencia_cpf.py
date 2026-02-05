"""
Script para verificar inconsistências de CPF no banco de dados
Investiga o caso do CPF 08934289147
"""
import pymysql
import sys

# Configurações do banco (mesmas do api_admissao.py)
DB_CONFIG = {
    'host': 'aplis.mysql.uhserver.com',
    'user': 'aplis',
    'password': 'aplis321*',
    'database': 'newdb',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def print_separator(title=""):
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)
    print()

def verificar_paciente_por_id(cod_paciente):
    """Verifica dados completos de um paciente pelo ID"""
    print_separator(f"VERIFICAÇÃO: Paciente ID {cod_paciente}")
    
    connection = None
    cursor = None
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        query = """
            SELECT 
                CodPaciente,
                NomPaciente,
                CPF,
                DtaNascimento,
                Sexo,
                TelCelular,
                RGNumero,
                RGOrgao,
                RGUF,
                NomMae,
                EstadoCivil
            FROM newdb.paciente
            WHERE CodPaciente = %s
        """
        
        cursor.execute(query, (cod_paciente,))
        resultado = cursor.fetchone()
        
        if resultado:
            print("✅ PACIENTE ENCONTRADO:")
            print(f"   ID Paciente: {resultado['CodPaciente']}")
            print(f"   Nome: {resultado['NomPaciente']}")
            print(f"   CPF: {resultado['CPF']}")
            print(f"   Data Nascimento: {resultado['DtaNascimento']}")
            print(f"   Sexo: {resultado['Sexo']} (1=Masculino, 2=Feminino)")
            print(f"   Telefone: {resultado['TelCelular']}")
            print(f"   RG: {resultado['RGNumero']} - {resultado['RGOrgao']}/{resultado['RGUF']}")
            print(f"   Nome da Mãe: {resultado['NomMae']}")
            print(f"   Estado Civil: {resultado['EstadoCivil']}")
            return resultado
        else:
            print(f"❌ Paciente com ID {cod_paciente} NÃO ENCONTRADO")
            return None
            
    except Exception as e:
        print(f"❌ ERRO ao buscar paciente: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def verificar_paciente_por_cpf(cpf):
    """Verifica todos os pacientes com um determinado CPF"""
    print_separator(f"VERIFICAÇÃO: Todos os pacientes com CPF {cpf}")
    
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    connection = None
    cursor = None
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        query = """
            SELECT 
                CodPaciente,
                NomPaciente,
                CPF,
                DtaNascimento,
                Sexo,
                TelCelular,
                RGNumero
            FROM newdb.paciente
            WHERE CPF = %s
            ORDER BY CodPaciente
        """
        
        cursor.execute(query, (cpf_limpo,))
        resultados = cursor.fetchall()
        
        if resultados:
            print(f"✅ ENCONTRADOS {len(resultados)} PACIENTE(S) COM ESTE CPF:")
            print()
            for idx, pac in enumerate(resultados, 1):
                print(f"   [{idx}] ID: {pac['CodPaciente']} | Nome: {pac['NomPaciente']}")
                print(f"       CPF: {pac['CPF']} | Nascimento: {pac['DtaNascimento']}")
                print(f"       Sexo: {pac['Sexo']} | Tel: {pac['TelCelular']} | RG: {pac['RGNumero']}")
                print()
            
            if len(resultados) > 1:
                print("⚠️  ATENÇÃO: DUPLICIDADE DE CPF DETECTADA!")
                print("   O mesmo CPF está cadastrado para múltiplos pacientes!")
            
            return resultados
        else:
            print(f"❌ Nenhum paciente encontrado com CPF {cpf_limpo}")
            return []
            
    except Exception as e:
        print(f"❌ ERRO ao buscar por CPF: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def verificar_nome_semelhante(nome):
    """Busca pacientes com nome semelhante"""
    print_separator(f"VERIFICAÇÃO: Pacientes com nome semelhante a '{nome}'")
    
    connection = None
    cursor = None
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Busca exata (case insensitive)
        query_exata = """
            SELECT 
                CodPaciente,
                NomPaciente,
                CPF,
                DtaNascimento,
                Sexo
            FROM newdb.paciente
            WHERE LOWER(NomPaciente) = LOWER(%s)
            ORDER BY CodPaciente
        """
        
        cursor.execute(query_exata, (nome,))
        resultados_exatos = cursor.fetchall()
        
        if resultados_exatos:
            print(f"✅ ENCONTRADOS {len(resultados_exatos)} PACIENTE(S) COM NOME EXATO:")
            for pac in resultados_exatos:
                print(f"   ID: {pac['CodPaciente']} | Nome: {pac['NomPaciente']}")
                print(f"   CPF: {pac['CPF']} | Nascimento: {pac['DtaNascimento']}")
                print()
        else:
            print("❌ Nenhum paciente encontrado com nome exato")
            
            # Busca parcial
            print("\n🔍 Tentando busca parcial...")
            palavras = nome.split()
            if len(palavras) >= 2:
                primeiro_nome = palavras[0]
                ultimo_nome = palavras[-1]
                
                query_parcial = """
                    SELECT 
                        CodPaciente,
                        NomPaciente,
                        CPF,
                        DtaNascimento
                    FROM newdb.paciente
                    WHERE LOWER(NomPaciente) LIKE LOWER(%s)
                    AND LOWER(NomPaciente) LIKE LOWER(%s)
                    ORDER BY CodPaciente
                    LIMIT 10
                """
                
                cursor.execute(query_parcial, (f'%{primeiro_nome}%', f'%{ultimo_nome}%'))
                resultados_parciais = cursor.fetchall()
                
                if resultados_parciais:
                    print(f"✅ ENCONTRADOS {len(resultados_parciais)} PACIENTE(S) COM NOME SEMELHANTE:")
                    for pac in resultados_parciais:
                        print(f"   ID: {pac['CodPaciente']} | Nome: {pac['NomPaciente']}")
                        print(f"   CPF: {pac['CPF']} | Nascimento: {pac['DtaNascimento']}")
                        print()
                else:
                    print("❌ Nenhum paciente encontrado com nome semelhante")
        
        return resultados_exatos
            
    except Exception as e:
        print(f"❌ ERRO ao buscar por nome: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def verificar_requisicao(cod_requisicao):
    """Verifica dados da requisição"""
    print_separator(f"VERIFICAÇÃO: Requisição {cod_requisicao}")
    
    connection = None
    cursor = None
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        query = """
            SELECT 
                r.IdRequisicao,
                r.CodRequisicao,
                r.CodPaciente,
                p.NomPaciente,
                p.CPF,
                r.DtaColeta,
                r.DadosClinicos
            FROM newdb.requisicao r
            LEFT JOIN newdb.paciente p ON r.CodPaciente = p.CodPaciente
            WHERE r.CodRequisicao = %s
        """
        
        cursor.execute(query, (cod_requisicao,))
        resultado = cursor.fetchone()
        
        if resultado:
            print("✅ REQUISIÇÃO ENCONTRADA:")
            print(f"   ID Requisição: {resultado['IdRequisicao']}")
            print(f"   Código: {resultado['CodRequisicao']}")
            print(f"   ID Paciente: {resultado['CodPaciente']}")
            print(f"   Nome Paciente: {resultado['NomPaciente']}")
            print(f"   CPF Paciente: {resultado['CPF']}")
            print(f"   Data Coleta: {resultado['DtaColeta']}")
            print(f"   Dados Clínicos: {resultado['DadosClinicos']}")
            return resultado
        else:
            print(f"❌ Requisição {cod_requisicao} NÃO ENCONTRADA")
            return None
            
    except Exception as e:
        print(f"❌ ERRO ao buscar requisição: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def main():
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "DIAGNÓSTICO DE INCONSISTÊNCIA DE CPF" + " "*22 + "║")
    print("╚" + "="*78 + "╝")
    
    # Caso específico: CPF 08934289147
    CPF_INVESTIGADO = "08934289147"
    PACIENTE_ID = 20490
    REQUISICAO = "0040000356004"
    NOME_KAUA = "KAUA LARSSON LOPES DE SOUSA"
    NOME_MANOELA = "MANOELA GOUVEIA CARNEIRO"
    
    print("\n📋 CASO EM INVESTIGAÇÃO:")
    print(f"   CPF: {CPF_INVESTIGADO}")
    print(f"   ID Paciente (banco): {PACIENTE_ID}")
    print(f"   Requisição: {REQUISICAO}")
    print(f"   Nome na Receita Federal: {NOME_KAUA}")
    print(f"   Nome no Banco: {NOME_MANOELA}")
    
    # 1. Verificar paciente ID 20490
    pac_20490 = verificar_paciente_por_id(PACIENTE_ID)
    
    # 2. Verificar todos com o CPF 08934289147
    pacs_com_cpf = verificar_paciente_por_cpf(CPF_INVESTIGADO)
    
    # 3. Verificar se existe paciente com nome KAUA
    verificar_nome_semelhante(NOME_KAUA)
    
    # 4. Verificar se existe paciente com nome MANOELA
    verificar_nome_semelhante(NOME_MANOELA)
    
    # 5. Verificar requisição
    verificar_requisicao(REQUISICAO)
    
    # RESUMO E DIAGNÓSTICO
    print_separator("DIAGNÓSTICO FINAL")
    
    print("🔍 ANÁLISE DA SITUAÇÃO:")
    print()
    
    if pac_20490:
        if pac_20490['CPF'] == CPF_INVESTIGADO:
            print("✅ Confirmado: Paciente ID 20490 tem CPF cadastrado como 08934289147")
            print(f"   Nome cadastrado: {pac_20490['NomPaciente']}")
        else:
            print(f"⚠️  CPF do paciente 20490 é diferente: {pac_20490['CPF']}")
    
    print()
    
    if len(pacs_com_cpf) > 1:
        print("🚨 PROBLEMA CRÍTICO: DUPLICIDADE DE CPF!")
        print(f"   O CPF {CPF_INVESTIGADO} está cadastrado para {len(pacs_com_cpf)} pacientes diferentes!")
        print()
        print("   📌 AÇÃO NECESSÁRIA:")
        print("   1. Verificar qual é o cadastro correto")
        print("   2. Corrigir o CPF do(s) cadastro(s) incorreto(s)")
        print("   3. Manter apenas 1 cadastro por CPF")
    elif len(pacs_com_cpf) == 1:
        print(f"✅ CPF {CPF_INVESTIGADO} está cadastrado para apenas 1 paciente")
        print(f"   Nome: {pacs_com_cpf[0]['NomPaciente']}")
        print()
        print("   📌 VERIFICAÇÃO:")
        print(f"   Este CPF pertence a '{NOME_KAUA}' segundo a Receita Federal")
        if pacs_com_cpf[0]['NomPaciente'].upper() != NOME_KAUA.upper():
            print(f"   ⚠️  DIVERGÊNCIA: Nome no banco é '{pacs_com_cpf[0]['NomPaciente']}'")
            print()
            print("   📌 AÇÃO NECESSÁRIA:")
            print("   1. Validar se o CPF foi digitado corretamente")
            print("   2. Se CPF estiver correto, atualizar o nome do paciente")
            print("   3. Se CPF estiver errado, corrigir para o CPF correto do paciente")
    else:
        print(f"❌ CPF {CPF_INVESTIGADO} não encontrado no banco")
    
    print()
    print("="*80)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
