# 🔒 Segurança e Configuração de Credenciais

## ⚠️ IMPORTANTE - NÃO COMITAR CHAVES REAIS

Este projeto utiliza variáveis de ambiente para proteger credenciais sensíveis.
**NUNCA** commite chaves de API, senhas ou tokens diretamente no código.

## 📋 Configuração Local

### 1. Backend (Python)

Copie o arquivo de exemplo e configure suas credenciais:

```bash
cd backend
cp .env.example .env
```

Edite o arquivo `backend/.env` com suas credenciais reais:

```env
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon-publica
SUPABASE_SERVICE_KEY=sua-service-role-key

# Banco de Dados MySQL
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua-senha-real
DB_NAME=newdb

# API de CPF
CPF_API_TOKEN=seu-token-real
```

### 2. Frontend (React)

Crie um arquivo `.env.local` na raiz do projeto:

```env
REACT_APP_SUPABASE_URL=https://seu-projeto.supabase.co
REACT_APP_SUPABASE_ANON_KEY=sua-chave-anon-publica
REACT_APP_SUPABASE_SERVICE_KEY=sua-service-role-key
```

## 🚫 Arquivos que NÃO devem ir para o Git

O `.gitignore` já está configurado para ignorar:

- `backend/.env` - Credenciais do backend
- `.env.production` - Credenciais de produção
- `.env.local` - Credenciais locais do React
- `testar_supabase_admin.html` - Arquivo de teste com chaves

## ✅ Verificação de Segurança

Antes de fazer commit, verifique:

```bash
# Buscar por possíveis credenciais expostas
git grep -i "password\|secret\|token\|key" -- ':!SECURITY.md' ':!*.example'
```

## 🔐 Boas Práticas

1. **Use variáveis de ambiente** para todas as credenciais
2. **Nunca hardcode** senhas ou tokens no código
3. **Mantenha .env.example** atualizado (sem valores reais)
4. **Rotacione credenciais** periodicamente
5. **Use diferentes credenciais** para desenvolvimento e produção

## 📞 Em caso de exposição acidental

Se você commitou credenciais por acidente:

1. **Revogue imediatamente** todas as chaves expostas
2. **Gere novas credenciais** 
3. **Remova do histórico do Git**:
   ```bash
   # Use git filter-branch ou BFG Repo-Cleaner
   # OU simplesmente apague o repositório e recrie
   ```

## 🔍 Obter suas Chaves

### Supabase
1. Acesse https://supabase.com/dashboard
2. Selecione seu projeto
3. Vá em **Settings** → **API**
4. Copie `URL`, `anon/public key` e `service_role key`

### CPF API
1. Acesse https://hubdodesenvolvedor.com.br/
2. Faça login ou crie uma conta
3. Gere seu token de API
