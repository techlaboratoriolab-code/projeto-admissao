# 🏗️ Arquitetura do Sistema

Documentação técnica da arquitetura do Sistema de Automação de Admissão Hospitalar.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura de Alto Nível](#arquitetura-de-alto-nível)
- [Componentes Frontend](#componentes-frontend)
- [Componentes Backend](#componentes-backend)
- [Fluxo de Dados](#fluxo-de-dados)
- [Segurança](#segurança)
- [Performance](#performance)
- [Escalabilidade](#escalabilidade)

---

## 🎯 Visão Geral

O sistema segue uma arquitetura **Cliente-Servidor** moderna com separação clara entre frontend e backend.

### Características Principais

- **SPA (Single Page Application)**: React no frontend
- **API RESTful**: Flask no backend
- **Autenticação Stateless**: JWT tokens
- **Banco de Dados**: MySQL (apLIS) + PostgreSQL (Supabase)
- **Armazenamento**: AWS S3 para documentos
- **OCR**: Google Vertex AI

---

## 🏛️ Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────┐
│                         USUÁRIO                              │
│                      (Navegador Web)                         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Pages      │  │  Components  │  │   Contexts   │      │
│  │              │  │              │  │              │      │
│  │ - Login      │  │ - Navbar     │  │ - Auth       │      │
│  │ - Admission  │  │ - PatientCard│  │ - Theme      │      │
│  │ - Users      │  │ - DocViewer  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            React Router (Rotas)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP REST API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (Flask)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Middleware Layer                        │   │
│  │  - CORS                                             │   │
│  │  - Auth (JWT Validation)                            │   │
│  │  - Rate Limiting                                    │   │
│  │  - Logging                                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ API Routes   │  │   Services   │  │   Utils      │      │
│  │              │  │              │  │              │      │
│  │ - /auth      │  │ - Database   │  │ - Validators │      │
│  │ - /paciente  │  │ - S3         │  │ - Formatters │      │
│  │ - /requisicao│  │ - OCR        │  │ - Cache      │      │
│  │ - /medicos   │  │ - apLIS API  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────┬────────────────┬────────────────┬─────────────┬──────┘
       │                │                │             │
       ▼                ▼                ▼             ▼
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐
│  Supabase  │  │   MySQL    │  │   AWS S3   │  │ Vertex AI│
│(PostgreSQL)│  │  (apLIS)   │  │(Documentos)│  │  (OCR)   │
│            │  │            │  │            │  │          │
│ - Users    │  │ - Pacientes│  │ - PDFs     │  │ - Extract│
│ - Auth     │  │ - Médicos  │  │ - Images   │  │ - Analyze│
│ - Logs     │  │ - Convênios│  │            │  │          │
└────────────┘  └────────────┘  └────────────┘  └──────────┘
```

---

## 🎨 Componentes Frontend

### Estrutura de Pastas

```
src/
├── components/          # Componentes reutilizáveis
│   ├── DocumentViewer.jsx
│   ├── Navbar.jsx
│   ├── PatientCard.jsx
│   └── PrivateRoute.jsx
│
├── contexts/           # Contextos React
│   ├── AuthContext.jsx    # Estado de autenticação
│   └── ThemeContext.jsx   # Tema claro/escuro
│
├── pages/              # Páginas principais
│   ├── AdmissionView.jsx  # Página de admissão
│   ├── LoginNew.jsx       # Página de login
│   └── UserManagement.jsx # Gestão de usuários
│
├── lib/                # Bibliotecas
│   └── supabase.js        # Cliente Supabase
│
├── utils/              # Utilitários
│   └── permissions.ts     # Gerenciamento de permissões
│
├── App.jsx             # Componente raiz
├── index.js            # Entry point
└── config.js           # Configurações
```

### Fluxo de Componentes

```
App.jsx
  └── Router
      ├── Public Routes
      │   └── LoginNew
      │
      └── Private Routes
          ├── Navbar
          │
          ├── AdmissionView
          │   ├── SearchBar
          │   ├── PatientList
          │   │   └── PatientCard (múltiplos)
          │   └── DocumentViewer
          │
          └── UserManagement (admin only)
              └── UserTable
```

### Contextos

#### AuthContext
Gerencia estado de autenticação global.

```javascript
{
  user: {
    id: string,
    email: string,
    name: string,
    role: 'user' | 'admin'
  },
  token: string,
  login: (email, password) => Promise,
  logout: () => void,
  isAuthenticated: boolean
}
```

#### ThemeContext
Gerencia tema da aplicação.

```javascript
{
  theme: 'light' | 'dark',
  toggleTheme: () => void
}
```

---

## 🐍 Componentes Backend

### Estrutura de Arquivos

```
backend/
├── api_admissao.py         # API principal
├── api_auth.py             # Endpoints de autenticação
├── auth.py                 # Middleware de autenticação
├── supabase_client.py      # Cliente Supabase
│
├── services/               # Camada de serviços (futuro)
│   ├── database.py
│   ├── s3.py
│   └── ocr.py
│
├── utils/                  # Utilitários (futuro)
│   ├── validators.py
│   ├── formatters.py
│   └── cache.py
│
├── requirements.txt        # Dependências
├── .env                    # Variáveis de ambiente
└── logs/                   # Logs da aplicação
```

### Camadas da API

#### 1. Middleware Layer

```python
# CORS - Permite requisições do frontend
CORS(app, origins=['http://localhost:3000'])

# Auth - Valida JWT token
@auth.require_auth
def protected_route():
    pass

# Rate Limiting - Previne abuso
rate_limiter.wait_if_needed()

# Logging - Registra todas as requisições
logger.info(f"Request: {request.method} {request.path}")
```

#### 2. Route Layer

Endpoints da API organizados por domínio:

```python
# Autenticação
@app.route('/api/auth/login', methods=['POST'])
@app.route('/api/auth/register', methods=['POST'])
@app.route('/api/auth/verify', methods=['GET'])

# Pacientes
@app.route('/api/buscar_paciente', methods=['GET'])
@app.route('/api/buscar_requisicao', methods=['GET'])

# Médicos
@app.route('/api/buscar_medico', methods=['GET'])
@app.route('/api/medicos', methods=['GET'])

# Instituições e Convênios
@app.route('/api/instituicoes', methods=['GET'])
@app.route('/api/convenios', methods=['GET'])

# Documentos
@app.route('/api/documento', methods=['GET'])
@app.route('/api/ocr', methods=['POST'])

# Usuários (Admin)
@app.route('/api/users', methods=['GET', 'POST'])
@app.route('/api/users/<id>', methods=['PUT', 'DELETE'])
```

#### 3. Service Layer

Lógica de negócio:

```python
# Database Service
def buscar_paciente_por_cpf(cpf):
    # Validar CPF
    # Buscar no banco
    # Formatar resultado
    return paciente

# S3 Service
def upload_documento(file, path):
    # Validar arquivo
    # Upload para S3
    # Retornar URL
    return url

# OCR Service
def extrair_dados_documento(file_path):
    # Carregar documento
    # Processar com Vertex AI
    # Extrair campos
    return dados_extraidos
```

---

## 🔄 Fluxo de Dados

### 1. Autenticação

```
User Input (Login Form)
  ↓
Frontend: AuthContext.login(email, password)
  ↓
POST /api/auth/login
  ↓
Backend: Validate credentials with Supabase
  ↓
Generate JWT token
  ↓
Return { token, user }
  ↓
Frontend: Store token in localStorage
  ↓
Frontend: Set user in AuthContext
  ↓
Redirect to /admissao
```

### 2. Busca de Paciente

```
User Input (CPF)
  ↓
Frontend: Validate CPF format
  ↓
GET /api/buscar_paciente?cpf=123456789
Headers: { Authorization: Bearer <token> }
  ↓
Backend: Validate JWT token
  ↓
Backend: Check cache
  ├─ Cache hit → Return cached data
  └─ Cache miss ↓
      Query MySQL database (apLIS)
        ↓
      Format data
        ↓
      Store in cache
        ↓
      Return data
  ↓
Frontend: Display PatientCard
```

### 3. Upload de Documento (Futuro)

```
User: Select file
  ↓
Frontend: Validate file (size, type)
  ↓
POST /api/upload with FormData
  ↓
Backend: Validate file
  ↓
Backend: Upload to S3
  ↓
Backend: Trigger OCR (if needed)
  ↓
Backend: Store metadata in database
  ↓
Return { url, ocr_data }
  ↓
Frontend: Display document
```

---

## 🔒 Segurança

### Camadas de Segurança

#### 1. Autenticação
- **JWT Tokens**: Assinados e com expiração
- **Supabase Auth**: Gerenciamento robusto de usuários
- **Password Hashing**: bcrypt com salt

#### 2. Autorização
- **Role-Based Access Control (RBAC)**: user/admin
- **Row Level Security (RLS)**: Supabase
- **Protected Routes**: Frontend e backend

#### 3. Validação
- **Input Validation**: Frontend e backend
- **SQL Injection Prevention**: Prepared statements
- **XSS Prevention**: React escapa automaticamente
- **CSRF Protection**: Tokens CSRF (futuro)

#### 4. Comunicação
- **HTTPS Only**: Em produção
- **CORS Configured**: Apenas origens permitidas
- **Headers de Segurança**: Helmet.js (futuro)

#### 5. Dados Sensíveis
- **Environment Variables**: Nunca no código
- **Secrets Management**: .env não versionado
- **Token Expiration**: Tokens expiram após 24h

### Middleware de Autenticação

```python
# auth.py
class Auth:
    def require_auth(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = self.get_token_from_header()
            
            if not token:
                return jsonify({'error': 'Token missing'}), 401
            
            user = self.verify_token(token)
            
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Armazena usuário no contexto
            g.current_user = user
            
            return f(*args, **kwargs)
        return decorated_function
```

---

## ⚡ Performance

### Otimizações Implementadas

#### Frontend
- **Code Splitting**: React.lazy() para rotas
- **Memoization**: useMemo, useCallback
- **Lazy Loading**: Componentes carregados sob demanda
- **Tailwind CSS**: Purge CSS não usado

#### Backend
- **Caching**: Redis (futuro) ou in-memory
- **Connection Pooling**: Database connections
- **Rate Limiting**: Previne sobrecarga
- **Logs Rotativos**: Evita disco cheio

#### Banco de Dados
- **Indexes**: Em campos frequentemente buscados
- **Query Optimization**: EXPLAIN para queries lentas
- **Connection Reuse**: Não abrir conexão a cada request

### Métricas

| Operação | Tempo Alvo | Atual |
|----------|-----------|-------|
| Login | < 1s | ~800ms |
| Busca CPF | < 2s | ~1.5s |
| Busca Nome | < 3s | ~2.5s |
| Load Documento | < 2s | ~1.8s |
| OCR | < 10s | ~8s |

---

## 📈 Escalabilidade

### Horizontal Scaling

```
Load Balancer
  ├── Frontend Instance 1 (Vercel Edge)
  ├── Frontend Instance 2
  └── Frontend Instance N

Load Balancer
  ├── Backend Instance 1
  ├── Backend Instance 2
  └── Backend Instance N
      │
      └── Shared Services
          ├── Database (Read Replicas)
          ├── Redis Cache
          └── S3 Storage
```

### Vertical Scaling

- **Database**: Upgrade para planos maiores
- **Backend**: Mais CPU/RAM por instância
- **Cache**: Aumentar tamanho do Redis

### Estratégias

#### 1. Stateless Backend
- Nenhum estado armazenado no servidor
- Permite múltiplas instâncias
- Load balancing fácil

#### 2. Caching Agressivo
- Cache de consultas frequentes
- TTL apropriado para cada tipo de dado
- Invalidação inteligente

#### 3. Database Optimization
- Read replicas para leituras
- Master para escritas
- Sharding por instituição (futuro)

#### 4. CDN para Assets
- Imagens e documentos via CDN
- Reduz carga no servidor
- Latência menor globalmente

---

## 🗄️ Banco de Dados

### Schema Supabase (PostgreSQL)

```sql
-- Tabela de usuários
CREATE TABLE public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de logs de acesso (opcional)
CREATE TABLE public.access_logs (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES public.users(id),
  action TEXT NOT NULL,
  resource TEXT,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_access_logs_user ON public.access_logs(user_id);
CREATE INDEX idx_access_logs_created ON public.access_logs(created_at);

-- RLS Policies
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own data"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Admins can view all"
  ON public.users FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE id = auth.uid() AND role = 'admin'
    )
  );
```

### Relacionamento com apLIS (MySQL)

O sistema **não modifica** o banco do apLIS, apenas lê:

- `pacientes`: Dados pessoais
- `requisicoes`: Pedidos de exames
- `medicos`: Médicos solicitantes
- `convenios`: Planos de saúde
- `instituicoes`: Hospitais/clínicas

---

## 🚀 Deploy Architecture (Produção)

```
                    Internet
                       │
                       ▼
              ┌────────────────┐
              │   CloudFlare   │ (CDN + DDoS Protection)
              └────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
  ┌─────────────┐            ┌─────────────┐
  │   Vercel    │            │   Render    │
  │  (Frontend) │            │  (Backend)  │
  └─────────────┘            └─────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐ ┌──────────┐   ┌──────────┐
            │   Supabase   │ │  MySQL   │   │  AWS S3  │
            │ (PostgreSQL) │ │ (apLIS)  │   │  (Docs)  │
            └──────────────┘ └──────────┘   └──────────┘
```

---

## 📊 Monitoramento

### Logs

```python
# Estrutura de logs
{
  "timestamp": "2026-02-05T10:30:00Z",
  "level": "INFO",
  "user_id": "uuid",
  "action": "buscar_paciente",
  "resource": "cpf:12345678900",
  "status": 200,
  "duration_ms": 145,
  "ip_address": "192.168.1.1"
}
```

### Métricas (Futuro)

- **Requests por minuto**
- **Tempo de resposta médio**
- **Taxa de erro**
- **Uso de cache (hit rate)**
- **Usuários ativos**

---

**Versão**: 1.0.0  
**Última atualização**: Fevereiro 2026
