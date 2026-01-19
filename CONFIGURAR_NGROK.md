# 🚀 Como Configurar o Sistema com Ngrok

## Situação Atual

Você tem **2 túneis ngrok** rodando:

1. **Backend (API)**: `https://scrubbier-songless-connor.ngrok-free.dev` → porta 5000
2. **Frontend (React)**: `https://automacaolab.ngrok.dev` → porta 3000

## ✅ O que foi corrigido

1. **CORS no backend** - aceita requisições de qualquer origem
2. **URLs dinâmicas** - imagens usam automaticamente a URL da requisição
3. **Arquivo de configuração centralizado** - `src/config.js`
4. **Todas as chamadas da API atualizadas** - usam a configuração centralizada

## 📝 Como Usar

### Passo 1: Iniciar o Backend
```bash
cd backend
python api_admissao.py
```

### Passo 2: Iniciar o Ngrok para o Backend
Em outro terminal:
```bash
ngrok http 5000
```

Você vai ver algo assim:
```
Forwarding  https://abc123.ngrok-free.dev -> http://localhost:5000
```

**COPIE essa URL!**

### Passo 3: Atualizar a Configuração do Frontend

Abra o arquivo: `src/config.js`

Encontre essa linha:
```javascript
const NGROK_API_URL = 'https://scrubbier-songless-connor.ngrok-free.dev';
```

Substitua pela nova URL do ngrok:
```javascript
const NGROK_API_URL = 'https://SUA-NOVA-URL.ngrok-free.dev';
```

Certifique-se que está assim:
```javascript
const USE_NGROK = true; // Deve estar true para usar ngrok
```

### Passo 4: Iniciar o Frontend
```bash
npm start
```

### Passo 5 (Opcional): Expor o Frontend via Ngrok

Se você quiser que outras pessoas acessem o frontend também:

```bash
ngrok http 3000 --domain=automacaolab.ngrok.dev
```

## 🔍 Como Testar

### Teste 1: Backend funcionando
Abra no navegador:
```
https://SUA-URL-NGROK.ngrok-free.dev/
```

Deve retornar um JSON com informações da API.

### Teste 2: Frontend conectando no backend
1. Abra o DevTools do navegador (F12)
2. Vá na aba Console
3. Você deve ver:
   ```
   🔧 CONFIGURAÇÃO DA API
   📍 Modo: NGROK (Produção/Remoto)
   🌐 URL da API: https://sua-url.ngrok-free.dev
   ✅ Configuração carregada com sucesso!
   ```

### Teste 3: Fazer uma busca de requisição
No frontend, digite um código de requisição e clique em "Buscar".

No console do backend, você deve ver os logs da requisição.

## 💡 Dicas

### Usar Localhost (Desenvolvimento Local)
Se você estiver desenvolvendo localmente e não precisar do ngrok, mude no `src/config.js`:

```javascript
const USE_NGROK = false; // Vai usar http://localhost:5000
```

### Ngrok Gratuito Expira
O ngrok gratuito gera uma nova URL toda vez que você reinicia.

Quando isso acontecer:
1. Copie a nova URL do terminal do ngrok
2. Atualize `NGROK_API_URL` no arquivo `src/config.js`
3. Reinicie o frontend (Ctrl+C e depois `npm start`)

### Usar Domínio Fixo (Plano Pago)
Se você tem ngrok pago com domínio fixo:

```bash
ngrok http 5000 --domain=meu-lab.ngrok.io
```

Aí você só precisa configurar uma vez no `src/config.js`.

## 📋 Checklist Rápido

Quando você for usar o sistema com ngrok:

- [ ] Backend rodando (`python api_admissao.py`)
- [ ] Ngrok rodando na porta 5000 (`ngrok http 5000`)
- [ ] URL do ngrok copiada
- [ ] `src/config.js` atualizado com a URL do ngrok
- [ ] `USE_NGROK = true` no config.js
- [ ] Frontend iniciado (`npm start`)
- [ ] Console do navegador mostrando a URL correta
- [ ] Teste de busca funcionando

## 🎯 Resumo

**Antes** (não funcionava):
- Frontend chamava `http://localhost:5000` (hardcoded em vários lugares)
- Quando acessava via ngrok, não funcionava

**Depois** (funciona):
- Frontend usa `API_BASE_URL` do arquivo de configuração
- Basta atualizar em 1 lugar só (`src/config.js`)
- Funciona tanto com localhost quanto com ngrok

Agora está tudo configurado e funcionando! 🎉
