# Como usar o sistema com Ngrok

## O que é Ngrok?
Ngrok cria um túnel seguro que expõe seu servidor local (localhost) para a internet, permitindo acesso remoto.

## Correções Aplicadas

### 1. CORS Configurado
O backend agora aceita requisições de qualquer origem (`origins: "*"`), incluindo URLs do ngrok.

### 2. URLs Dinâmicas
As URLs das imagens agora são geradas dinamicamente baseadas no host da requisição, funcionando tanto com:
- `http://localhost:5000`
- `https://seu-dominio.ngrok.io`

## Como Usar

### Passo 1: Iniciar o Backend
```bash
cd backend
python api_admissao.py
```

O backend vai iniciar em `http://localhost:5000`

### Passo 2: Iniciar o Ngrok para o Backend
Em outro terminal, execute:

```bash
ngrok http 5000
```

Você vai ver algo assim:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:5000
```

**COPIE essa URL!** (exemplo: `https://abc123.ngrok.io`)

### Passo 3: Configurar o Frontend
No seu frontend React, atualize a URL base da API para usar a URL do ngrok:

```javascript
// Exemplo: src/config.js ou onde você configura a URL da API
const API_BASE_URL = 'https://abc123.ngrok.io';  // Substitua pela sua URL do ngrok
```

### Passo 4: Iniciar o Frontend
```bash
npm start
```

### Passo 5 (Opcional): Expor o Frontend também
Se você quiser expor o frontend via ngrok:

```bash
ngrok http 3000
```

## Testando

1. Acesse o endpoint de health check do ngrok:
   ```
   https://abc123.ngrok.io/api/health
   ```

2. Você deve receber:
   ```json
   {
     "status": "online",
     "servico": "API Admissão apLIS",
     "timestamp": "2026-01-19T..."
   }
   ```

## Problemas Comuns

### 1. Erro de CORS
- ✅ JÁ CORRIGIDO: O backend agora aceita requisições de qualquer origem

### 2. Imagens não carregam
- ✅ JÁ CORRIGIDO: URLs agora são dinâmicas e se adaptam ao host (ngrok ou localhost)

### 3. Ngrok expira
- Ngrok gratuito expira após algumas horas e gera uma nova URL
- Quando isso acontecer, você precisa:
  1. Reiniciar o ngrok
  2. Atualizar a URL no frontend
  3. Reiniciar o frontend

### 4. Limite de requisições
- Plano gratuito do ngrok tem limite de requisições/minuto
- Se atingir o limite, espere alguns minutos ou considere upgrade

## Dicas de Segurança

⚠️ **IMPORTANTE**: Seu arquivo `.env` contém credenciais sensíveis!

Quando expor via ngrok:
- Não compartilhe suas credenciais AWS/Google
- Considere usar autenticação básica no ngrok:
  ```bash
  ngrok http 5000 --basic-auth "usuario:senha"
  ```
- Monitore os logs para detectar acessos não autorizados

## Configuração Avançada (Opcional)

### Fixar domínio ngrok (Plano Pago)
Se você tem plano pago do ngrok, pode fixar um domínio:

```bash
ngrok http 5000 --domain=meu-lab.ngrok.io
```

Aí você pode configurar no `.env`:
```
API_BASE_URL=https://meu-lab.ngrok.io
```

### Usar ngrok config file
Crie um arquivo `ngrok.yml`:

```yaml
version: "2"
authtoken: SEU_TOKEN_AQUI
tunnels:
  backend:
    proto: http
    addr: 5000
  frontend:
    proto: http
    addr: 3000
```

Execute:
```bash
ngrok start --all
```

## Resumo dos Comandos

```bash
# Terminal 1: Backend
cd backend
python api_admissao.py

# Terminal 2: Ngrok para Backend
ngrok http 5000

# Terminal 3: Frontend (atualize a URL da API antes!)
npm start

# Terminal 4 (Opcional): Ngrok para Frontend
ngrok http 3000
```

## Verificação Rápida

✅ Backend rodando em `http://localhost:5000`
✅ Ngrok expondo backend em `https://abc123.ngrok.io`
✅ CORS configurado para aceitar qualquer origem
✅ URLs dinâmicas funcionando
✅ Frontend configurado com URL do ngrok

Agora seu sistema deve funcionar perfeitamente com ngrok!
