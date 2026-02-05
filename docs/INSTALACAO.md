# Guia de Instalação - Sistema de Automação de Admissão

## 📋 Pré-requisitos

Antes de começar a instalação, certifique-se de ter os seguintes softwares instalados:

### Obrigatórios
- ✅ **Node.js** (versão 16 ou superior)
  - Download: https://nodejs.org/
  - Verificar: `node --version`
  
- ✅ **Python** (versão 3.9 ou superior)
  - Download: https://www.python.org/downloads/
  - Verificar: `python --version`
  
- ✅ **Git**
  - Download: https://git-scm.com/downloads
  - Verificar: `git --version`

### Contas Necessárias
- ✅ **Supabase** (gratuito)
  - Criar conta: https://supabase.com/
  
- ⚠️ **AWS** (opcional - para documentos)
  - Criar conta: https://aws.amazon.com/
  
- ⚠️ **Google Cloud** (opcional - para OCR)
  - Criar conta: https://cloud.google.com/

---

## 🚀 Instalação Passo a Passo

### 1. Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd automacao-admissao
```

### 2. Instalação Automática (Recomendado para Windows)

Execute o script de instalação:

```bash
instalar_tudo.bat
```

**O que este script faz:**
- Instala todas as dependências do Node.js
- Instala todas as dependências do Python
- Cria estrutura de pastas necessárias
- Prepara o ambiente

### 3. Instalação Manual

Se preferir instalar manualmente ou estiver em Linux/Mac:

#### a) Instalar dependências do Frontend

```bash
npm install
```

#### b) Instalar dependências do Backend

```bash
cd backend
pip install -r requirements.txt
cd ..
```

#### c) Criar estrutura de logs

```bash
# Windows
mkdir backend\logs

# Linux/Mac
mkdir -p backend/logs
```

---

## ⚙️ Configuração

### 1. Configurar Supabase

#### a) Criar Projeto no Supabase
1. Acesse https://supabase.com/
2. Clique em "New Project"
3. Preencha os dados:
   - Nome do projeto
   - Senha do banco de dados (guarde esta senha!)
   - Região (escolha a mais próxima)

#### b) Obter Credenciais
1. No dashboard do Supabase, vá em **Settings → API**
2. Copie:
   - **URL**: A URL do seu projeto
   - **anon public**: Sua chave pública
   - **service_role**: Sua chave de serviço (nunca exponha no frontend!)

#### c) Configurar Banco de Dados
1. No Supabase, vá em **SQL Editor**
2. Execute o seguinte SQL:

```sql
-- Desabilitar confirmação de email (desenvolvimento)
UPDATE auth.config
SET email_confirm = false;

-- Criar tabela de usuários
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Habilitar RLS (Row Level Security)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Política: usuários podem ver seus próprios dados
CREATE POLICY "Usuários podem ver seus próprios dados"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

-- Política: admins podem ver todos
CREATE POLICY "Admins podem ver todos"
  ON public.users FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE id = auth.uid() AND role = 'admin'
    )
  );
```

### 2. Configurar Arquivo .env (Backend)

Crie um arquivo `.env` na pasta `backend/`:

```bash
cd backend
# Windows: usar notepad
notepad .env

# Linux/Mac: usar vim ou nano
nano .env
```

Cole o seguinte conteúdo e preencha com seus dados:

```env
# =====================================
# SUPABASE - Autenticação
# =====================================
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=sua-chave-anon-publica-aqui
SUPABASE_SERVICE_KEY=sua-service-role-key-aqui

# =====================================
# BANCO DE DADOS - apLIS (MySQL)
# =====================================
DB_HOST=seu-servidor-mysql.com
DB_PORT=3306
DB_USER=usuario_banco
DB_PASSWORD=senha_banco
DB_NAME=nome_banco_aplis

# =====================================
# AWS S3 - Documentos (OPCIONAL)
# =====================================
AWS_ACCESS_KEY_ID=sua-access-key
AWS_SECRET_ACCESS_KEY=sua-secret-key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=nome-do-bucket

# =====================================
# GOOGLE CLOUD - Vertex AI (OPCIONAL)
# =====================================
GOOGLE_PROJECT_ID=seu-projeto-gcp
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=backend/credenciais-gcp.json

# =====================================
# API apLIS
# =====================================
APLIS_BASE_URL=http://192.168.1.100:8080
APLIS_USUARIO=usuario-api
APLIS_SENHA=senha-api

# =====================================
# CONFIGURAÇÕES DA API
# =====================================
PORT=5000
FLASK_ENV=development
FLASK_DEBUG=True
```

### 3. Configurar Frontend (config.js)

Edite o arquivo `src/config.js`:

```javascript
const config = {
  // URL do backend
  apiUrl: process.env.NODE_ENV === 'production' 
    ? 'https://seu-backend.com' 
    : 'http://localhost:5000',
  
  // Supabase
  supabaseUrl: 'https://SEU-PROJETO.supabase.co',
  supabaseKey: 'sua-chave-anon-publica-aqui'
};

export default config;
```

---

## 🎯 Primeiro Uso

### 1. Criar Usuário Administrador

Execute o script:

```bash
criar_admin.bat
```

Ou manualmente:

```bash
cd backend
python resetar_senha_admin.py
```

Siga as instruções para criar o primeiro usuário admin.

### 2. Iniciar o Sistema

Execute:

```bash
iniciar_sistema.bat
```

Ou manualmente:

```bash
# Terminal 1 - Backend
cd backend
python api_admissao.py

# Terminal 2 - Frontend
npm start
```

### 3. Acessar o Sistema

Abra o navegador em:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

Faça login com o usuário admin criado.

---

## ✅ Verificação da Instalação

### Verificar Node.js e NPM

```bash
node --version    # Deve mostrar v16.0.0 ou superior
npm --version     # Deve mostrar 7.0.0 ou superior
```

### Verificar Python e Pip

```bash
python --version  # Deve mostrar 3.9.0 ou superior
pip --version     # Deve mostrar 21.0 ou superior
```

### Verificar Dependências do Frontend

```bash
npm list react react-dom react-router-dom
```

### Verificar Dependências do Backend

```bash
cd backend
pip list | findstr "flask supabase requests"
```

### Testar Conexão com Supabase

```bash
cd backend
python -c "from supabase_client import supabase_manager; print('✅ Supabase conectado!' if supabase_manager.is_connected() else '❌ Erro na conexão')"
```

---

## 🐛 Problemas Comuns

### Erro: "Node não é reconhecido"

**Problema**: Node.js não instalado ou não está no PATH

**Solução**:
1. Reinstale o Node.js
2. Durante a instalação, marque "Add to PATH"
3. Reinicie o terminal

### Erro: "Python não é reconhecido"

**Problema**: Python não instalado ou não está no PATH

**Solução**:
1. Reinstale o Python
2. Durante a instalação, marque "Add Python to PATH"
3. Reinicie o terminal

### Erro: "pip install failed"

**Problema**: Pip desatualizado ou sem permissões

**Solução**:
```bash
# Atualizar pip
python -m pip install --upgrade pip

# Se precisar de admin (Windows)
# Execute o terminal como Administrador
```

### Erro: "Cannot find module"

**Problema**: Dependências não instaladas corretamente

**Solução**:
```bash
# Frontend
rm -rf node_modules package-lock.json
npm install

# Backend
pip install -r requirements.txt --force-reinstall
```

### Erro: "Port 3000 already in use"

**Problema**: Porta já está sendo usada

**Solução**:
```bash
# Encontrar processo
netstat -ano | findstr :3000

# Matar processo (substitua PID)
taskkill /PID <numero-do-pid> /F

# Ou usar outra porta
set PORT=3001 && npm start
```

### Erro: "Supabase connection failed"

**Problema**: Credenciais incorretas ou projeto inativo

**Solução**:
1. Verifique `SUPABASE_URL` e `SUPABASE_KEY` no `.env`
2. Acesse o dashboard do Supabase e verifique se o projeto está ativo
3. Regenere as chaves se necessário

---

## 📦 Estrutura Após Instalação

```
automacao-admissao/
├── node_modules/           ✅ Criado após npm install
├── backend/
│   ├── __pycache__/       ✅ Criado após executar Python
│   ├── logs/              ✅ Criado manualmente ou por script
│   └── .env               ✅ Criado manualmente
├── build/                  ⚠️ Criado após npm run build
└── .gitignore             ✅ Já existe
```

---

## 🎓 Próximos Passos

Após a instalação bem-sucedida:

1. ✅ **Leia o README.md** para entender o sistema
2. ✅ **Configure os dados de teste** (CSVs na pasta dados/)
3. ✅ **Crie usuários** através da interface de administração
4. ✅ **Teste as funcionalidades** principais
5. ✅ **Configure AWS e GCP** (se necessário)

---

## 📞 Suporte

Se encontrar problemas durante a instalação:

1. Verifique os logs em `backend/logs/`
2. Consulte a seção de Troubleshooting no README.md
3. Entre em contato com o suporte

---

**Boa sorte! 🚀**
