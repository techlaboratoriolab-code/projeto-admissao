# Guia Rápido - Teste do Ngrok

## URLs para Testar

Baseado no log, seu ngrok está em: `https://scrubbier-songless-connor.ngrok-free.dev`

### 1. Página Inicial (raiz)
```
https://scrubbier-songless-connor.ngrok-free.dev/
```
**Resultado esperado**: JSON com informações da API e lista de endpoints

### 2. Health Check
```
https://scrubbier-songless-connor.ngrok-free.dev/api/health
```
**Resultado esperado**:
```json
{
  "status": "online",
  "servico": "API Admissão apLIS",
  "timestamp": "2026-01-19T..."
}
```

### 3. Teste de Conexão com apLIS
```
https://scrubbier-songless-connor.ngrok-free.dev/api/admissao/teste
```

### 4. Buscar Requisição (exemplo)
```
https://scrubbier-songless-connor.ngrok-free.dev/api/requisicao/0040000356004
```

## O que estava acontecendo

Você estava acessando a **raiz** (`/`) do servidor, mas o Flask só tinha rotas começando com `/api/`.

Agora a raiz (`/`) retorna informações sobre a API em vez de 404.

## Próximos Passos

### No Frontend React

Atualize a URL base da API no seu código React para usar o ngrok:

```javascript
// Antes (localhost):
const API_BASE_URL = 'http://localhost:5000';

// Depois (ngrok):
const API_BASE_URL = 'https://scrubbier-songless-connor.ngrok-free.dev';
```

### Testar uma Requisição Completa

Você pode testar com curl:

```bash
curl https://scrubbier-songless-connor.ngrok-free.dev/api/health
```

Ou no navegador, acesse diretamente:
```
https://scrubbier-songless-connor.ngrok-free.dev/
```

## Problemas Resolvidos

✅ CORS configurado para aceitar qualquer origem
✅ URLs dinâmicas (imagens vão usar a URL do ngrok automaticamente)
✅ Rota raiz (`/`) criada para não dar mais 404
✅ Logging completo para debug
✅ Todas as rotas da API funcionando

## Observação

Se você está vendo `http://` no log mas o ngrok gera `https://`, isso é normal. O ngrok faz o SSL/TLS por você. Use sempre HTTPS na URL pública.
