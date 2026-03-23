# 🏥 Sistema de Automação de Admissão 

Sistema completo para automação do processo de admissão hospitalar com React + Flask + Supabase.

**Responsável**: Kaua
**Área**: Cadastro/Admissão
**Status**: Em teste
**Local de Execução**: PC

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)](https://python.org/)

---

## 🚀 Quick Start

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd automacao-admissao

# 2. Instale as dependências
scripts\instalar_tudo.bat

# 3. Configure o ambiente
# Edite backend/.env com suas credenciais

# 4. Crie um admin
scripts\criar_admin.bat

# 5. Inicie o sistema
scripts\iniciar_sistema.bat
```

Acesse: **http://localhost:3000**

---

## ✨ Funcionalidades

- 🔍 **Busca inteligente** de pacientes por CPF ou nome
- 👤 **Autenticação segura** com Supabase e JWT
- 📊 **Dashboard completo** de admissões
- 📄 **Gestão de documentos** com AWS S3
- 🤖 **OCR automático** com Google Vertex AI
- 👥 **Gerenciamento de usuários** e permissões
- 🎨 **Interface moderna** com Tailwind CSS
- 📱 **Design responsivo** mobile-first

---

## �️ Tecnologias

**Frontend**
- React 18.2 + React Router
- Tailwind CSS
- Supabase Client

**Backend**
- Flask 3.0
- Supabase (PostgreSQL)
- MySQL (apLIS)
- AWS S3
- Google Vertex AI

---

## 📁 Estrutura do Projeto

```
automacao-admissao/
│
├── 📂 backend/                  # Backend Python Flask
│   ├── api_admissao.py         # API principal de admissão
│   ├── api_auth.py             # API de autenticação
│   ├── auth.py                 # Middleware de autenticação
│   ├── supabase_client.py      # Cliente Supabase
│   ├── requirements.txt        # Dependências Python
│   ├── .env.example            # Template de variáveis
│   └── logs/                   # Logs da aplicação
│
├── 📂 src/                      # Frontend React
│   ├── components/             # Componentes reutilizáveis
│   ├── contexts/               # Contextos React
│   ├── pages/                  # Páginas da aplicação
│   ├── lib/                    # Bibliotecas
│   ├── utils/                  # Utilitários
│   ├── App.jsx                 # Componente principal
│   ├── index.js                # Entry point
│   └── config.js               # Configurações
│
├── 📂 scripts/                  # Scripts de automação
│   ├── instalar_tudo.bat       # Instala dependências
│   ├── iniciar_sistema.bat     # Inicia sistema completo
│   ├── iniciar_publico.bat     # Inicia apenas frontend
│   ├── criar_admin.bat         # Cria usuário admin
│   ├── resetar_login.bat       # Reseta senha
│   └── preparar_git.bat        # Prepara para Git
│
├── 📂 sql/                      # Scripts SQL
│   ├── promover_admin.sql      # Promove usuário para admin
│   ├── supabase_disable_email_confirmation.sql
│   └── supabase_fix_users.sql  # Corrige tabela users
│
├── 📂 docs/                     # Documentação completa
│   ├── INSTALACAO.md           # Guia de instalação
│   ├── API.md                  # Documentação da API
│   ├── DEPLOY.md               # Guia de deploy
│   ├── ARCHITECTURE.md         # Arquitetura do sistema
│   ├── CONTRIBUTING.md         # Como contribuir
│   ├── SCRIPTS.md              # Guia de scripts
│   ├── CHANGELOG.md            # Histórico de versões
│   └── DOCS.md                 # Índice da documentação
│
├── 📂 dados/                    # Dados auxiliares (CSV)
│   ├── convenios_extraidos_*.csv
│   ├── instituicoes_extraidas_*.csv
│   └── medicos_extraidos_*.csv
│
├── 📂 webservice/               # Scripts de integração
│   └── webservice.py           # Webservice apLIS
│
├── 📂 public/                   # Arquivos públicos
│   └── index.html              # HTML base
│
├── 📄 README.md                 # Este arquivo
├── 📄 .gitignore               # Arquivos ignorados
├── 📄 package.json             # Dependências Node.js
├── 📄 tailwind.config.js       # Configuração Tailwind
└── 📄 tsconfig.json            # Configuração TypeScript
```

---

## ⚙️ Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Node.js 16+** e npm
- **Python 3.9+** e pip
- **MySQL** ou acesso a banco de dados apLIS
- **Conta Supabase** (gratuita disponível)
- **Conta AWS** com S3 configurado (opcional)
- **Google Cloud** com Vertex AI habilitado (opcional)

---

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd automacao-admissao
```

### 2. Instalação Automática (Windows)

Execute o script de instalação:

```bash
scripts\instalar_tudo.bat
```

Este script irá:
- Instalar dependências do Node.js
- Instalar dependências do Python
- Criar estrutura de logs

### 3. Instalação Manual

#### Frontend
```bash
npm install
```

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

---

## 🔐 Configuração

### 1. Backend (.env)

Crie um arquivo `.env` na pasta `backend/` com as seguintes variáveis:

```env
# Supabase - Autenticação e Banco
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon-publica
SUPABASE_SERVICE_KEY=sua-service-role-key

# Banco de Dados apLIS (MySQL)
DB_HOST=seu-host-mysql
DB_USER=seu-usuario
DB_PASSWORD=sua-senha
DB_NAME=nome-do-banco

# AWS S3 - Documentos
AWS_ACCESS_KEY_ID=sua-access-key
AWS_SECRET_ACCESS_KEY=sua-secret-key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=nome-do-bucket

# Google Cloud - Vertex AI (OCR)
GOOGLE_PROJECT_ID=seu-projeto-gcp
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=caminho/para/credenciais.json

# API apLIS
APLIS_BASE_URL=http://ip-servidor:porta
APLIS_USUARIO=usuario-api
APLIS_SENHA=senha-api

# Configurações da API
PORT=5000
FLASK_ENV=development
```

### 2. Frontend (config.js)

Edite o arquivo `src/config.js`:

```javascript
const config = {
  apiUrl: 'http://localhost:5000', // URL do backend
  supabaseUrl: 'https://seu-projeto.supabase.co',
  supabaseKey: 'sua-chave-anon-publica'
};

export default config;
```

### 3. Supabase - Configuração de Banco

Execute os seguintes scripts SQL no Supabase SQL Editor:

#### a) Desabilitar confirmação de email (desenvolvimento):
```sql
-- supabase_disable_email_confirmation.sql
UPDATE auth.config
SET email_confirm = false;
```

#### b) Criar tabelas necessárias:
```sql
-- Tabela de usuários
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Habilitar RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Políticas de acesso
CREATE POLICY "Usuários podem ver seus próprios dados"
  ON public.users FOR SELECT
  USING (auth.uid() = id);
```

---

## 🚀 Como Usar

### Iniciar o Sistema Completo

```bash
scripts\iniciar_sistema.bat
```

Este comando inicia:
- **Backend Flask** na porta 5000
- **Frontend React** na porta 3000

### Iniciar Apenas o Frontend

```bash
scripts\iniciar_publico.bat
# ou
npm start
```

### Iniciar Apenas o Backend

```bash
cd backend
python api_admissao.py
```

### Criar Usuário Administrador

```bash
scripts\criar_admin.bat
```

Ou manualmente:
```bash
cd backend
python resetar_senha_admin.py
```

---

## ✨ Funcionalidades

### 1. **Busca de Pacientes**
- Busca por CPF, nome ou código de requisição
- Integração com apLIS
- Cache inteligente para otimização
- Paginação de resultados

### 2. **Visualização de Dados**
- Informações completas do paciente
- Dados de requisição
- Médico solicitante
- Convênio e instituição
- Documentos anexados

### 3. **Gestão de Documentos**
- Upload de documentos para AWS S3
- Visualização inline de PDFs e imagens
- Download de documentos
- OCR automático com Vertex AI

### 4. **Autenticação e Autorização**
- Login seguro via Supabase
- Diferentes níveis de acesso (user, admin)
- Proteção de rotas
- Sessão persistente

### 5. **Gerenciamento de Usuários** (Admin)
- Criar novos usuários
- Editar permissões
- Desativar usuários
- Resetar senhas

### 6. **Histórico e Logs**
- Registro de todas as ações
- Logs rotativos (5 arquivos de 10MB)
- Rastreamento de erros
- Métricas de uso

---

## 📡 API Endpoints

### Autenticação

#### POST `/api/auth/login`
Login de usuário
```json
{
  "email": "user@example.com",
  "password": "senha123"
}
```

#### POST `/api/auth/register`
Registro de novo usuário
```json
{
  "email": "user@example.com",
  "password": "senha123",
  "name": "Nome do Usuário"
}
```

#### GET `/api/auth/verify`
Verifica token de autenticação
- Headers: `Authorization: Bearer <token>`

### Admissão

#### GET `/api/buscar_paciente?cpf=12345678900`
Busca paciente por CPF

#### GET `/api/buscar_paciente?nome=JOAO`
Busca paciente por nome

#### GET `/api/buscar_requisicao?cod=12345`
Busca dados completos de requisição

#### GET `/api/buscar_medico?crm=12345&uf=SP`
Busca médico por CRM e UF

#### GET `/api/instituicoes`
Lista todas as instituições

#### GET `/api/convenios`
Lista todos os convênios

### Documentos

#### GET `/api/documento?path=caminho/arquivo.pdf`
Faz download de documento do S3

#### POST `/api/ocr`
Extrai dados de documento via OCR
```json
{
  "document_path": "s3://bucket/path/documento.pdf"
}
```

### Usuários (Admin)

#### GET `/api/users`
Lista todos os usuários

#### POST `/api/users`
Cria novo usuário

#### PUT `/api/users/:id`
Atualiza usuário

#### DELETE `/api/users/:id`
Remove usuário

---

## 🗄️ Banco de Dados

### Supabase (PostgreSQL)

#### Tabela `users`
```sql
id          UUID PRIMARY KEY
email       TEXT UNIQUE NOT NULL
name        TEXT
role        TEXT DEFAULT 'user'
created_at  TIMESTAMP DEFAULT NOW()
```

#### Tabela `access_logs` (opcional)
```sql
id          SERIAL PRIMARY KEY
user_id     UUID REFERENCES users(id)
action      TEXT
timestamp   TIMESTAMP DEFAULT NOW()
details     JSONB
```

### MySQL (apLIS)

O sistema integra com as seguintes tabelas do apLIS:
- `pacientes` - Dados dos pacientes
- `requisicoes` - Requisições de exames
- `medicos` - Cadastro de médicos
- `convenios` - Convênios médicos
- `instituicoes` - Instituições de saúde

---

## 🔒 Autenticação

### Fluxo de Autenticação

1. **Login**: Usuário envia email e senha
2. **Supabase**: Valida credenciais
3. **JWT Token**: Retorna token de acesso
4. **Armazenamento**: Token salvo no localStorage
5. **Requisições**: Token enviado no header `Authorization`

### Níveis de Acesso

- **user**: Acesso básico à visualização de dados
- **admin**: Acesso total, incluindo gestão de usuários

### Middleware de Autenticação

Todas as rotas protegidas utilizam o decorator `@auth.require_auth`:

```python
from auth import auth

@app.route('/api/protected')
@auth.require_auth
def protected_route():
    user = auth.get_current_user()
    return jsonify({'user': user})
```

---

## 🌐 Deploy

### Frontend (Vercel/Netlify)

1. Build da aplicação:
```bash
npm run build
```

2. Deploy da pasta `build/`:
- **Vercel**: `vercel --prod`
- **Netlify**: Arraste a pasta `build/` no dashboard

### Backend (Heroku/Railway/Render)

1. Adicione `Procfile`:
```
web: cd backend && python api_admissao.py
```

2. Configure variáveis de ambiente no painel
3. Deploy via Git:
```bash
git push heroku main
```

### Variáveis de Ambiente em Produção

Certifique-se de configurar todas as variáveis do arquivo `.env` no ambiente de produção.

---

## 🐛 Troubleshooting

### Erro: "Module not found"

**Problema**: Dependências não instaladas
**Solução**:
```bash
npm install
cd backend && pip install -r requirements.txt
```

### Erro: "Supabase connection failed"

**Problema**: Configuração incorreta do Supabase
**Solução**:
1. Verifique `SUPABASE_URL` e `SUPABASE_KEY` no `.env`
2. Teste a conexão no Supabase Dashboard
3. Verifique se o projeto está ativo

### Erro: "MySQL connection refused"

**Problema**: Banco de dados inacessível
**Solução**:
1. Verifique credenciais no `.env`
2. Teste conexão: `telnet DB_HOST 3306`
3. Verifique firewall e permissões

### Erro: "CORS policy blocked"

**Problema**: Frontend e backend em domínios diferentes
**Solução**:
1. Verifique configuração CORS no `api_admissao.py`
2. Adicione origem permitida:
```python
CORS(app, origins=['http://localhost:3000', 'https://seu-dominio.com'])
```

### Performance lenta

**Problema**: Muitas requisições ou dados grandes
**Solução**:
1. Habilite cache de convenios/médicos/instituições
2. Use paginação nos resultados
3. Otimize queries SQL
4. Considere CDN para documentos

---

## 📝 Scripts Úteis

### Windows Batch Scripts

- `instalar_tudo.bat` - Instala todas as dependências
- `iniciar_sistema.bat` - Inicia backend e frontend
- `iniciar_publico.bat` - Inicia apenas frontend
- `criar_admin.bat` - Cria usuário administrador
- `resetar_login.bat` - Reseta senha de usuário

### SQL Scripts

- `promover_admin.sql` - Promove usuário para admin
- `supabase_disable_email_confirmation.sql` - Desabilita confirmação de email
- `supabase_fix_users.sql` - Corrige tabela de usuários

---

## 👥 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📚 Documentação Completa

| Documento | Descrição |
|-----------|-----------|
| 📖 [Instalação](docs/INSTALACAO.md) | Guia detalhado de setup |
| 📡 [API](docs/API.md) | Referência completa da API |
| 🚀 [Deploy](docs/DEPLOY.md) | Como colocar em produção |
| 🏗️ [Arquitetura](docs/ARCHITECTURE.md) | Estrutura do sistema |
| 🤝 [Contribuir](docs/CONTRIBUTING.md) | Guia para devs |
| 📜 [Scripts](docs/SCRIPTS.md) | Todos os comandos |
| 📝 [Changelog](docs/CHANGELOG.md) | Histórico de versões |

---

## 🎯 Próximos Passos

1. ⚙️ Configure `backend/.env` com suas credenciais
2. 📖 Leia a [documentação completa](docs/DOCS.md)
3. 🚀 Faça o [deploy em produção](docs/DEPLOY.md)
4. 🤝 [Contribua](docs/CONTRIBUTING.md) com o projeto

---

## 📄 Licença

Este projeto é proprietário. Todos os direitos reservados.

---

## 💬 Suporte

- 📧 Email: tech.laboratorio.lab@gmail.com      

---

**Desenvolvido com ❤️ para otimizar processos do lab**
