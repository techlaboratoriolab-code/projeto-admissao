# Teste da Nova Metodologia de API - Requisição Listar

## Resumo das Mudanças

A API de admissão foi atualizada com a nova metodologia baseada em `requisicaoListar` do arquivo `apiaplisreduzido.py`.

### Principais Mudanças:

1. **Função Genérica**: `fazer_requisicao_aplis(cmd, dat)`
   - Centraliza todas as requisições ao apLIS
   - Padroniza logging e tratamento de erros
   - Facilita manutenção e debugging

2. **Nova Função**: `listar_requisicoes_aplis()`
   - Usa o comando `requisicaoListar`
   - Parâmetros: `idEvento`, `periodoIni`, `periodoFim`, `ordenar`
   - Retorna lista de requisições em um período

3. **Novo Endpoint**: `/api/requisicoes/listar (POST)`
   - Expõe a listagem de requisições via HTTP
   - Aceita parâmetros de filtro

4. **Logging Melhorado**:
   - Todas as requisições são logadas com prefixo `[apLIS]`
   - Payload e resposta aparecem nos logs
   - Facilita debugging e auditoria

## Como Usar

### 1. Listar Requisições do apLIS

**Endpoint**: `POST /api/requisicoes/listar`

**Request Body**:
```json
{
    "idEvento": "50",
    "periodoIni": "2026-01-15",
    "periodoFim": "2026-01-15",
    "ordenar": "IdRequisicao"
}
```

**Response**:
```json
{
    "sucesso": 1,
    "dados": {
        "sucesso": 1,
        "requisicoes": [
            {
                "IdRequisicao": "...",
                "CodRequisicao": "...",
                "...": "..."
            }
        ]
    },
    "mensagem": "Listagem obtida com sucesso"
}
```

### 2. Salvar Admissão (Atualizada)

A função `salvar_admissao_aplis()` agora usa a metodologia genérica:

**Código**:
```python
# Antes (antigo)
payload = {
    "ver": 1,
    "cmd": "admissaoSalvar",
    "dat": dados_admissao
}
response = requests.post(APLIS_URL, auth=(...), headers=APLIS_HEADERS, data=json.dumps(payload))

# Depois (novo)
resultado = fazer_requisicao_aplis("admissaoSalvar", dados_admissao)
```

### 3. Estrutura Padrão de Requisição ao apLIS

Todas as requisições seguem o padrão:

```json
{
    "ver": 1,
    "cmd": "nomeDoComando",
    "dat": {
        "campo1": "valor1",
        "campo2": "valor2"
    }
}
```

## Exemplos de Teste com cURL

### Listar requisições
```bash
curl -X POST http://localhost:5000/api/requisicoes/listar \
  -H "Content-Type: application/json" \
  -d '{
    "idEvento": "50",
    "periodoIni": "2026-01-15",
    "periodoFim": "2026-01-15"
  }'
```

### Testar conexão com apLIS
```bash
curl http://localhost:5000/api/health
```

## Implementação em Frontend

### JavaScript/React

```javascript
// Listar requisições
async function listarRequisicoes(idEvento, periodoIni, periodoFim) {
    const response = await fetch('http://localhost:5000/api/requisicoes/listar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            idEvento,
            periodoIni,
            periodoFim,
            ordenar: 'IdRequisicao'
        })
    });
    
    const data = await response.json();
    return data;
}

// Usar
listarRequisicoes('50', '2026-01-15', '2026-01-15').then(console.log);
```

## Compatibilidade

- ✅ Totalmente compatível com código antigo
- ✅ Usa a mesma estrutura de payload do apLIS
- ✅ Mantém todos os endpoints existentes funcionais
- ✅ Adiciona novos endpoints sem quebrar os antigos

## Logging

Os logs agora incluem:
- `[apLIS]` para requisições ao apLIS
- `[Listagem]` para operações de listagem
- `[Admissão]` para operações de admissão
- `[Consolidar]`, `[OCR]`, `[BUSCAR EXAMES]` para outras operações

Veja os arquivos de log em: `backend/logs/api_admissao.log`

## Próximas Melhorias

1. ✅ Adicionar suporte a mais comandos (exemplo: `requisicaoEditar`, `requisiçãoDeletar`)
2. ✅ Implementar cache de requisições
3. ✅ Adicionar filtros mais avançados
4. ✅ Suporte a paginação

---

**Data da Atualização**: 2026-01-19  
**Versão**: 2.0  
**Status**: ✅ Testado e Funcional
