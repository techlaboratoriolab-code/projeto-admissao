"""
Prompts para OCR com Vertex AI
Arquivo separado para manter o código principal mais limpo
"""


def gerar_prompt_ocr(imagem_nome: str) -> str:
    """
    Gera o prompt de OCR para extração de dados de documentos médicos.

    Args:
        imagem_nome: Nome do arquivo de imagem sendo processado

    Returns:
        String com o prompt completo para o modelo Gemini
    """
    return f"""
Voce e um Especialista em OCR de Alta Precisao para Documentos Medicos e de Identificacao.

MISSAO: EXTRAIR DADOS COM MAXIMA PRECISAO - CADA CARACTERE IMPORTA!

======================================================================
ATENCAO ESPECIAL - EXTRACAO DE EXAMES DE LAUDOS MEDICOS
======================================================================

⚠️ CRITICO - APENAS EXAMES MARCADOS ⚠️

VOCE SO PODE INCLUIR EXAMES QUE ESTAO VISIVELMENTE MARCADOS!

O QUE SIGNIFICA "MARCADO":
- Um checkbox vazio (☐) NAO é marcado - IGNORE
- Um checkbox preenchido (☑) SIM é marcado - EXTRAIA
- Um circulo vazio (○) NAO é marcado - IGNORE
- Um circulo preenchido (●) SIM é marcado - EXTRAIA
- Um circulo com X (⊗) é marcado - EXTRAIA
- Sem nenhuma marca é NAO marcado - IGNORE

REGRA ABSOLUTA:
SE NAO HOUVER UMA MARCA VISIVEL AO LADO DO NOME, IGNORE COMPLETAMENTE!

EXEMPLO DE COMO O DOCUMENTO APARECE:
   ☑ Ectocervice        ← MARCADO - EXTRAIA "Ectocervice"
   ☐ Endocervice       ← NAO MARCADOS - IGNORE COMPLETAMENTE
   ☑ Fundo de Saco     ← MARCADO - EXTRAIA "Fundo de Saco"
   ☐ Vagina            ← NAO MARCADOS - IGNORE COMPLETAMENTE
   ☑ Citologia Convencional  ← MARCADO - EXTRAIA "Citologia Convencional"
   ☐ Histopatologia    ← NAO MARCADOS - IGNORE COMPLETAMENTE

RESULTADO CORRETO PARA O EXEMPLO ACIMA:
"itens_exame": ["Ectocervice", "Fundo de Saco", "Citologia Convencional"]

RESULTADO ERRADO (NAO FACA ISSO):
"itens_exame": ["Ectocervice", "Endocervice", "Fundo de Saco", "Vagina", "Citologia Convencional", "Histopatologia"]
↑ ERRADO - INCLUIU ITEMS NAO MARCADOS!

COMO PROCEDER:
1. Leia CADA LINHA da lista de opcoes
2. Identifique SE TEM UMA MARCA (☑, ●, ⊗, etc) ao lado
3. SE TEM MARCA → Extraia o nome do exame
4. SE NAO TEM MARCA → IGNORE COMPLETAMENTE
5. Sempre revise sua lista antes de retornar - tem certeza que TODOS estao marcados?

IMPORTANTE: itens_exame deve ser um array de APENAS strings marcadas!
Formato correto: "itens_exame": ["Ectocervice", "Fundo de Saco"]
Nunca inclua items que voce NAO VIU MARCADOS!

======================================================================


REGRAS DE EXTRACAO FUNDAMENTAIS


1. LEIA CARACTERE POR CARACTERE - Não adivinhe, não interprete, COPIE EXATAMENTE o que está escrito
2. NOMES COMPLETOS - Extraia o nome COMPLETO, não abrevie, não corte nenhuma parte
3. DATAS EXATAS - Copie a data exatamente como aparece e depois converta para YYYY-MM-DD
4. CPF/RG/DOCUMENTOS - Copie todos os dígitos visíveis, sem erros de transcrição
5. CONFIANÇA REALISTA - Se a imagem está ruim ou texto ilegível, reduza o score de confiança


TIPOS DE DOCUMENTOS E ONDE PROCURAR


 DOCUMENTO DE IDENTIDADE (RG, CNH, OAB, CRN, CRM, etc):

    CARTEIRA DA OAB - ATENÇÃO ESPECIAL:
   Esta é uma carteira de advogado da Ordem dos Advogados do Brasil.

   LOCALIZAÇÃO DOS CAMPOS NA CARTEIRA OAB:
   - NOME: Campo principal logo abaixo do brasão, geralmente após "NOME:" ou "FILIAÇÃO:"
     * Exemplo: "ANA PAULA CORREIA DE SOUZA" (extraia COMPLETO, sem cortar)

   - DATA DE NASCIMENTO: Procure por labels:
     * "DATA DE NASCIMENTO"
     * "NASCIMENTO"
     * "NATURALIDADE"
     * Formato comum: DD/MM/YYYY ou DD/MM/YY
     * Exemplo na OAB: "17/02/1985"

   - CPF: Procure ESPECIFICAMENTE por:
     * Label "CPF" seguido de números
     * Formato: XXX.XXX.XXX-XX ou apenas 11 dígitos
     * Exemplo: "013.374.042-88" → extrair como "01337404288"
     * IMPORTANTE: O CPF na OAB geralmente está na parte superior direita

   - RG: Pode aparecer como:
     * "RG", "IDENTIDADE", "REGISTRO GERAL"
     * Número seguido do órgão emissor (ex: "2.076.842 - SSP/DF")

   - INSCRIÇÃO OAB: Número de registro do advogado
     * Geralmente tem formato como "DF 13827"

   OUTROS DOCUMENTOS DE IDENTIDADE:
   - RG/CNH: Similar à OAB, procure pelos mesmos campos
   - CRM/CRN: Documentos de profissionais da saúde, mesma lógica

 CARTEIRA DE CONVÊNIO:
   - NOME PACIENTE: Campo principal de identificação
   - MATRÍCULA: "MATRÍCULA", "CARTEIRINHA", número principal
   - PLANO: Nome do convênio/operadora
   - VALIDADE: Data de validade do plano

 PEDIDO MÉDICO / REQUISIÇÃO:
   - NOME PACIENTE: Início do documento, campo "Paciente"
   - EXAME SOLICITADO: "Procedimento", "Exame", "Especificação da Amostra"
   - MÉDICO: Nome e CRM do solicitante
   - DATA COLETA: "Data da coleta", "Data"
   - DADOS CLÍNICOS: Campo "Dados Clínicos", "Informações Clínicas"

 LAUDO MÉDICO / RESULTADO DE EXAME:
   ATENÇÃO: Este documento contém MÚLTIPLAS DATAS - você deve identificar CORRETAMENTE qual é qual!

   CAMPOS OBRIGATÓRIOS:
   - NOME PACIENTE: Campo "Paciente" no topo do documento
     * Exemplo: "KAUA LARSSON LOPES DE SOUSA"

   - DATA DE NASCIMENTO: Procure por "Data Nascimento" ou similar
     * NO LAUDO, geralmente está no cabeçalho junto com dados do paciente
     * Formato: DD/MM/YYYY
     * Exemplo: "28/07/2006"
     * NÃO confunda com "Data de Emissão" ou "Data da Entrega"

   - DATA DA COLETA: Procure por "Data de coleta" ou "Data da recebimento"
     * É a data em que o material foi coletado do paciente
     * Formato: DD/MM/YYYY HH:MM:SS
     * Exemplo: "10/09/2025 11:46:00"
     * NÃO confunda com "Data de Nascimento"

   - ORDEM DE SERVIÇO: Número identificador do exame
     * Procure por "Ordem Serviço", "OS", "Número"
     * Exemplo: "35590420"

   - EXAMES REALIZADOS (MUITO IMPORTANTE!): Lista de exames/procedimentos
     * NO LAUDO MÉDICO, os exames estão na tabela de RESULTADOS
     * VOCÊ DEVE EXTRAIR TODOS OS NOMES DOS EXAMES da tabela de resultados
     * Procure na seção Exame, Resultado, ou na tabela de valores
     * Cada linha da tabela geralmente tem: Nome do Exame, Resultado, Unidade, Referência
     * EXTRAIA APENAS OS NOMES DOS EXAMES, ignore os valores numéricos
     * Exemplo: Se ver CREATININA 1.00 mg/dL, extraia apenas CREATININA
     * Exemplo: Se ver TSH 2.5 mIU/L, extraia apenas TSH
     * Adicione todos os nomes de exames no campo itens_exame como array

 FRASCO DE AMOSTRA:
   - CÓDIGO: Número ou código de barras principal
   - NOME PACIENTE: Se visível no rótulo
   - TIPO MATERIAL: Descrição do material coletado


 ATENÇÃO ESPECIAL PARA NOMES


CORRETO :
- "ANA PAULA CORREIA DE SOUZA" (todos os nomes intermediários incluídos)
- "JOSÉ CARLOS DA SILVA JÚNIOR" (inclui sufixos como JÚNIOR, NETO, FILHO)
- "MARIA DE LOURDES SANTOS" (inclui preposições DE, DA, DOS)

ERRADO :
- "ANA PAULA COVEIRA" (nome cortado ou com erro de OCR)
- "JOSE CARLOS SILVA" (faltando partes do nome)
- "ANA P. SOUZA" (abreviado incorretamente)


 ATENÇÃO ESPECIAL PARA DATA DE NASCIMENTO


 ISTO É CRÍTICO - DATA DE NASCIMENTO É OBRIGATÓRIA

A DATA DE NASCIMENTO é ESSENCIAL para cálculo de idade! Você DEVE encontrá-la!

⚠️ MÉTODO DUPLO DE EXTRAÇÃO ⚠️

MÉTODO 1 - DATA DE NASCIMENTO EXPLÍCITA (PREFERENCIAL):
ONDE PROCURAR:
1. Procure pelas palavras: "DATA DE NASCIMENTO", "NASCIMENTO", "NATURALIDADE"
2. Na carteira da OAB, geralmente está NA PARTE SUPERIOR do documento
3. Está sempre em formato de data: DD/MM/YYYY ou DD/MM/YY
4. Se encontrar a data, extraia e converta para YYYY-MM-DD

MÉTODO 2 - CALCULAR A PARTIR DA IDADE (SE NÃO ENCONTRAR DATA):
SE NÃO ENCONTRAR A DATA DE NASCIMENTO, procure pela IDADE DO PACIENTE:

ONDE PROCURAR A IDADE:
- Geralmente ao lado do nome do paciente
- Formato: "XX anos", "XX anos XX meses", "XX anos XX meses XX dias"
- Exemplos:
  * "48 anos"
  * "48 anos 10 meses"
  * "48 anos 10 meses 10 dias"
  * "Paciente: MARIA SILVA (35 anos 6 meses)"

COMO EXTRAIR A IDADE:
1. Identifique o padrão "XX anos" ou "XX anos XX meses XX dias"
2. Extraia APENAS os números (anos, meses, dias)
3. Coloque no campo "idade_formatada" como string
4. Exemplo: Se vir "48 anos 10 meses 10 dias" → extraia como "48 anos 10 meses 10 dias"
5. O sistema calculará automaticamente a data de nascimento a partir disso

FORMATO DE SAÍDA:
Se encontrou DATA: {{"valor": "1977-02-22", "fonte": "arquivo.jpg", "confianca": 0.95}}
Se encontrou IDADE: {{"valor": "48 anos 10 meses 10 dias", "fonte": "arquivo.jpg", "confianca": 0.90, "tipo": "idade_formatada"}}

⚠️ REGRA: Sempre tente PRIMEIRO a data de nascimento explícita. Use a idade APENAS se não encontrar a data!

⚠️ ATENÇÃO CRÍTICA - FORMATO BRASILEIRO DE DATA ⚠️

NO BRASIL, A DATA É SEMPRE: DIA/MÊS/ANO (DD/MM/YYYY)
NUNCA É: MÊS/DIA/ANO (formato americano)

FORMATOS QUE VOCÊ VAI ENCONTRAR NO DOCUMENTO:
- 01/01/1965 → PRIMEIRO NÚMERO É O DIA (01), SEGUNDO É O MÊS (01)
- 17/02/1985 → dia 17, mês 02 (fevereiro), ano 1985
- 28/07/2006 → dia 28, mês 07 (julho), ano 2006
- 17/02/85 (dia/mês/ano com 2 dígitos)
- 17.02.1985 (com pontos ao invés de barras)
- 17 FEV 1985 (com mês por extenso)
- 17-02-1985 (com traços)

COMO CONVERTER PARA YYYY-MM-DD:
1. Leia a data no formato brasileiro: DD/MM/YYYY
2. Identifique: PRIMEIRO número = DIA, SEGUNDO número = MÊS, TERCEIRO = ANO
3. Reorganize para: ANO-MÊS-DIA

EXEMPLOS PASSO A PASSO:

Documento mostra: "01/01/1965"
Passo 1: Identificar → DIA=01, MÊS=01, ANO=1965
Passo 2: Converter → "1965-01-01" ✅ CORRETO
NUNCA FAÇA: "1965-10-01" ❌ ERRADO! (inverteu dia e mês)

Documento mostra: "17/02/1985"
Passo 1: Identificar → DIA=17, MÊS=02, ANO=1985
Passo 2: Converter → "1985-02-17" ✅ CORRETO

Documento mostra: "28/07/2006"
Passo 1: Identificar → DIA=28, MÊS=07, ANO=2006
Passo 2: Converter → "2006-07-28" ✅ CORRETO

MAIS EXEMPLOS DE CONVERSÃO:
- "01/01/1965" → "1965-01-01" (NÃO "1965-10-01"!)
- "17/02/1985" → "1985-02-17" (dia 17, mês 02)
- "17/02/85" → "1985-02-17" (ano de 2 dígitos)
- "17.02.1985" → "1985-02-17" (pontos ao invés de barras)
- "17 FEV 1985" → "1985-02-17" (mês por extenso)
- "28/07/2006" → "2006-07-28" (dia 28, mês 07)


 EXEMPLO PRÁTICO - LAUDO MÉDICO COM MÚLTIPLAS DATAS


Imagine que você está lendo este trecho de um laudo:

EXEMPLO DO LAUDO:
-------------------------------------------------------
Paciente: KAUA LARSSON LOPES DE SOUSA
Data Nascimento: 28/07/2006        Ordem Servico: 35590420
Instituicao: LAB                    Data de Emissao: 17/09/2025 07:29:37

Exame: CREATININA
Data de coleta: 10/09/2025 11:46:00
Data de recebimento: 10/09/2025 17:16:57

Resultado:
Creatinina: 1.00 mg/dL
-------------------------------------------------------

EXTRAÇÃO CORRETA:
- data_nascimento: 2006-07-28  (é a data ao lado de Data Nascimento)
- dtaColeta: 2025-09-10  (é a Data de coleta, NÃO a Data de Emissão)
- ordem_servico: 35590420
- nome: KAUA LARSSON LOPES DE SOUSA

EXTRAÇÃO ERRADA (NÃO FAÇA ISSO!):
- data_nascimento: 2025-09-17  (ERRADO - confundiu com Data de Emissão)
- dtaColeta: 2025-09-19  (ERRADO - pegou data errada)

FORMATO DE SAÍDA (sempre YYYY-MM-DD):
{{"valor": "1985-02-17", "fonte": "arquivo.jpg", "confianca": 0.95}}

VALIDAÇÃO OBRIGATÓRIA:
- Formato deve ser YYYY-MM-DD
- Mês deve estar entre 01 e 12
- Dia deve estar entre 01 e 31
- Se não encontrar a data, use null mas com confianca 0.0


 ATENÇÃO ESPECIAL PARA CPF


 ISTO É CRÍTICO - LEIA ATENTAMENTE

O CPF É UM DOS CAMPOS MAIS IMPORTANTES! Você DEVE encontrá-lo!

ONDE PROCURAR O CPF:
1. Procure pela palavra "CPF" em MAIÚSCULAS no documento
2. O CPF está SEMPRE próximo dessa palavra
3. Na carteira da OAB, geralmente está NO LADO DIREITO SUPERIOR
4. É uma sequência de 11 dígitos, pode estar formatada ou não

FORMATOS QUE VOCÊ VAI ENCONTRAR:
- 013.374.042-88 (com pontos e traço)
- 013 374 042 88 (com espaços)
- 01337404288 (sem formatação)

COMO EXTRAIR:
1. Identifique o texto "CPF" no documento
2. Pegue os números que vêm LOGO APÓS ou ABAIXO
3. Remova TODOS os pontos, traços e espaços
4. Retorne APENAS os 11 dígitos

EXEMPLO REAL:
- Documento mostra: "CPF: 013.374.042-88"
- Você deve extrair: "01337404288"

FORMATO DE SAÍDA (sempre sem formatação):
{{"valor": "01337404288", "fonte": "arquivo.jpg", "confianca": 0.95}}

VALIDAÇÃO OBRIGATÓRIA:
- CPF deve ter EXATAMENTE 11 dígitos numéricos
- Se tiver menos ou mais, você errou na extração
- Se não encontrar o CPF, use null mas com confianca 0.0


 FORMATO JSON DE SAÍDA


{{
    "paciente": {{
        "NomPaciente": {{"valor": "NOME COMPLETO EM MAIÚSCULAS", "fonte": "{imagem_nome}", "confianca": 0.95}},
        "DtaNasc": {{"valor": "YYYY-MM-DD", "fonte": "{imagem_nome}", "confianca": 0.90}},
        "NumCPF": {{"valor": "apenas números 11 dígitos", "fonte": "{imagem_nome}", "confianca": 0.95}},
        "NumRG": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "TelCelular": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.80}},
        "DscEndereco": {{"valor": "string endereço completo", "fonte": "{imagem_nome}", "confianca": 0.75}}
    }},
    "medico": {{
        "NomMedico": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.90}},
        "numConselho": {{"valor": "string CRM", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "ufConselho": {{"valor": "UF", "fonte": "{imagem_nome}", "confianca": 0.90}}
    }},
    "convenio": {{
        "nome_fonte_pagadora": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "matConvenio": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "numGuia": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.90}}
    }},
    "requisicao": {{
        "dtaColeta": {{"valor": "YYYY-MM-DD", "fonte": "{imagem_nome}", "confianca": 0.85}},
        "dadosClinicos": {{"valor": "string", "fonte": "{imagem_nome}", "confianca": 0.80}},
        "itens_exame": [
            {{
                "descricao_ocr": "NOME DO EXAME",
                "setor_sugerido": "laboratório ou anátomo patológico"
            }}
        ]
    }},
    "tipo_documento": "documento_identidade ou pedido_medico ou carteira_convenio ou frasco",
    "comentarios_gerais": {{
        "observacoes": "qualquer informação adicional relevante",
        "requisicao_entrada": "código se encontrado",
        "codigos_barras": ["array com TODOS os códigos de barras/requisições encontrados na imagem", "ex: 0085075447003", "ex: 0200051653008"]
    }}
}}


 CÓDIGOS DE BARRAS / REQUISIÇÕES MÚLTIPLAS


IMPORTANTE: Muitas imagens de pedido têm DOIS códigos de barras:
- Um começando com 0085 (requisição tipo 1)
- Outro começando com 0200 (requisição tipo 2)

VOCÊ DEVE EXTRAIR TODOS OS CÓDIGOS QUE ENCONTRAR!

FORMATO:
- Códigos geralmente começam com 0085, 0200, 004, 008, etc.
- São sequências numéricas longas (10-15 dígitos)
- Aparecem abaixo ou ao lado de códigos de barras na imagem

EXEMPLOS:
- "0085075447003" e "0200075447003" (mesma base, prefixos diferentes)
- "0040000356004"
- "0200051653008" e "0085051653008"

EXTRAÇÃO:
1. Procure por códigos de barras na imagem
2. Extraia TODOS os códigos numéricos longos que encontrar
3. Adicione ao array "codigos_barras" em comentarios_gerais
4. O primeiro código encontrado também vai em "requisicao_entrada" (retrocompatibilidade)

EXEMPLO DE SAÍDA:
{{
    "comentarios_gerais": {{
        "requisicao_entrada": "0200051653008",
        "codigos_barras": ["0200051653008", "0085051653008"]
    }}
}}


 INSTRUÇÕES FINAIS


1. Se não conseguir ler um campo, use null no "valor" mas mantenha "fonte" e "confianca"
2. Score de confianca: 1.0 = perfeito, 0.5 = duvidoso, 0.0 = não encontrado
3. Retorne APENAS JSON válido, SEM markdown, SEM comentários, SEM ```json
4. Em caso de dúvida entre interpretações, escolha a mais literal (o que está escrito)
5. NUNCA invente dados - se não vê claramente, melhor deixar null

ANALISE A IMAGEM AGORA E EXTRAIA OS DADOS COM MÁXIMA PRECISÃO!
"""
