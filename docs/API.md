# API Documentation

## Visão Geral

Esta API fornece endpoints para o sistema de automação de admissão hospitalar, incluindo busca de pacientes, gerenciamento de documentos e autenticação de usuários.

**Base URL**: `http://localhost:5000`

**Autenticação**: Bearer Token (JWT) no header `Authorization`

---

## 🔐 Autenticação

### POST `/api/auth/login`
Autentica um usuário e retorna um token JWT.

**Request Body:**
```json
{
  "email": "usuario@exemplo.com",
  "password": "senha123"
}
```

**Response (200):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid-do-usuario",
    "email": "usuario@exemplo.com",
    "name": "Nome do Usuário",
    "role": "user"
  }
}
```

**Erros:**
- `400`: Email ou senha não fornecidos
- `401`: Credenciais inválidas
- `500`: Erro interno do servidor

---

### POST `/api/auth/register`
Registra um novo usuário no sistema.

**Request Body:**
```json
{
  "email": "novo@exemplo.com",
  "password": "senha123",
  "name": "Nome do Usuário"
}
```

**Response (201):**
```json
{
  "success": true,
  "user": {
    "id": "uuid-do-usuario",
    "email": "novo@exemplo.com",
    "name": "Nome do Usuário"
  }
}
```

**Erros:**
- `400`: Dados faltando ou inválidos
- `409`: Email já cadastrado
- `500`: Erro interno

---

### GET `/api/auth/verify`
Verifica se o token JWT é válido.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "valid": true,
  "user": {
    "id": "uuid",
    "email": "usuario@exemplo.com",
    "role": "user"
  }
}
```

**Erros:**
- `401`: Token inválido ou expirado

---

## 👤 Busca de Pacientes

### GET `/api/buscar_paciente`
Busca paciente por CPF ou nome.

**Autenticação**: Requerida

**Query Parameters:**
- `cpf` (string, opcional): CPF do paciente (apenas números)
- `nome` (string, opcional): Nome do paciente (mínimo 3 caracteres)
- `pagina` (int, opcional): Número da página (padrão: 1)
- `limite` (int, opcional): Registros por página (padrão: 50)

**Exemplo:**
```
GET /api/buscar_paciente?cpf=12345678900
GET /api/buscar_paciente?nome=JOAO&pagina=1&limite=20
```

**Response (200):**
```json
{
  "success": true,
  "dados": [
    {
      "cod_paciente": "12345",
      "nome": "JOAO DA SILVA",
      "cpf": "123.456.789-00",
      "data_nascimento": "1990-01-01",
      "sexo": "M",
      "idade": "34 anos",
      "telefone": "(11) 98765-4321",
      "email": "joao@exemplo.com"
    }
  ],
  "total": 1,
  "pagina_atual": 1,
  "total_paginas": 1,
  "fonte": "apLIS"
}
```

**Erros:**
- `400`: Parâmetros inválidos
- `404`: Paciente não encontrado
- `500`: Erro na busca

---

### GET `/api/buscar_requisicao`
Busca dados completos de uma requisição.

**Autenticação**: Requerida

**Query Parameters:**
- `cod` (string, required): Código da requisição

**Exemplo:**
```
GET /api/buscar_requisicao?cod=2024001234
```

**Response (200):**
```json
{
  "success": true,
  "paciente": {
    "cod_paciente": "12345",
    "nome": "JOAO DA SILVA",
    "cpf": "123.456.789-00",
    "data_nascimento": "1990-01-01",
    "sexo": "M",
    "telefone": "(11) 98765-4321"
  },
  "requisicao": {
    "cod_requisicao": "2024001234",
    "data_requisicao": "2024-02-05 10:30:00",
    "status": "Em análise",
    "tipo": "Exame Laboratorial"
  },
  "medico": {
    "cod_medico": "789",
    "nome": "DR. MARIA SANTOS",
    "crm": "123456",
    "uf": "SP",
    "especialidade": "Cardiologia"
  },
  "convenio": {
    "cod_convenio": "456",
    "nome": "UNIMED",
    "tipo": "Particular"
  },
  "instituicao": {
    "cod_instituicao": "101",
    "nome": "HOSPITAL SAO LUCAS",
    "endereco": "Rua das Flores, 123"
  },
  "documentos": [
    {
      "tipo": "Pedido Médico",
      "url": "https://bucket.s3.amazonaws.com/docs/pedido_123.pdf",
      "data_upload": "2024-02-05T10:30:00Z"
    }
  ]
}
```

**Erros:**
- `400`: Código não fornecido
- `404`: Requisição não encontrada
- `500`: Erro na busca

---

## 👨‍⚕️ Médicos

### GET `/api/buscar_medico`
Busca médico por CRM e UF.

**Autenticação**: Requerida

**Query Parameters:**
- `crm` (string, required): Número do CRM
- `uf` (string, required): UF do CRM (2 letras)

**Exemplo:**
```
GET /api/buscar_medico?crm=123456&uf=SP
```

**Response (200):**
```json
{
  "success": true,
  "medico": {
    "cod_medico": "789",
    "nome": "DR. MARIA SANTOS",
    "crm": "123456",
    "uf": "SP",
    "especialidade": "Cardiologia",
    "telefone": "(11) 3456-7890",
    "email": "dra.maria@exemplo.com"
  }
}
```

**Erros:**
- `400`: CRM ou UF não fornecidos
- `404`: Médico não encontrado

---

### GET `/api/medicos`
Lista todos os médicos cadastrados.

**Autenticação**: Requerida

**Response (200):**
```json
{
  "success": true,
  "medicos": [
    {
      "cod_medico": "789",
      "nome": "DR. MARIA SANTOS",
      "crm": "123456",
      "uf": "SP"
    },
    // ... mais médicos
  ],
  "total": 150
}
```

---

## 🏥 Instituições

### GET `/api/instituicoes`
Lista todas as instituições cadastradas.

**Autenticação**: Requerida

**Query Parameters:**
- `nome` (string, opcional): Filtrar por nome
- `pagina` (int, opcional): Número da página
- `limite` (int, opcional): Registros por página

**Response (200):**
```json
{
  "success": true,
  "instituicoes": [
    {
      "cod_instituicao": "101",
      "nome": "HOSPITAL SAO LUCAS",
      "endereco": "Rua das Flores, 123",
      "cidade": "São Paulo",
      "uf": "SP",
      "telefone": "(11) 3456-7890"
    }
  ],
  "total": 50
}
```

---

## 💳 Convênios

### GET `/api/convenios`
Lista todos os convênios cadastrados.

**Autenticação**: Requerida

**Response (200):**
```json
{
  "success": true,
  "convenios": [
    {
      "cod_convenio": "456",
      "nome": "UNIMED",
      "tipo": "Particular",
      "ativo": true
    }
  ],
  "total": 30
}
```

---

## 📄 Documentos

### GET `/api/documento`
Faz download de um documento do S3.

**Autenticação**: Requerida

**Query Parameters:**
- `path` (string, required): Caminho do documento no S3

**Exemplo:**
```
GET /api/documento?path=documentos/2024/02/pedido_123.pdf
```

**Response (200):**
- Content-Type: application/pdf (ou image/jpeg, etc)
- Arquivo binário

**Erros:**
- `400`: Path não fornecido
- `404`: Documento não encontrado
- `500`: Erro no download

---

### POST `/api/ocr`
Extrai texto de documento usando OCR (Vertex AI).

**Autenticação**: Requerida

**Request Body:**
```json
{
  "document_path": "s3://bucket/docs/documento.pdf",
  "extract_fields": ["nome", "cpf", "data_nascimento"]
}
```

**Response (200):**
```json
{
  "success": true,
  "extracted_data": {
    "nome": "JOAO DA SILVA",
    "cpf": "123.456.789-00",
    "data_nascimento": "01/01/1990"
  },
  "raw_text": "Texto completo extraído...",
  "confidence": 0.95
}
```

**Erros:**
- `400`: Path não fornecido
- `500`: Erro no OCR

---

## 👥 Gerenciamento de Usuários (Admin)

### GET `/api/users`
Lista todos os usuários do sistema.

**Autenticação**: Requerida (Admin)

**Response (200):**
```json
{
  "success": true,
  "users": [
    {
      "id": "uuid",
      "email": "usuario@exemplo.com",
      "name": "Nome do Usuário",
      "role": "user",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 10
}
```

**Erros:**
- `403`: Sem permissão (não é admin)

---

### POST `/api/users`
Cria um novo usuário.

**Autenticação**: Requerida (Admin)

**Request Body:**
```json
{
  "email": "novo@exemplo.com",
  "password": "senha123",
  "name": "Novo Usuário",
  "role": "user"
}
```

**Response (201):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "novo@exemplo.com",
    "name": "Novo Usuário",
    "role": "user"
  }
}
```

---

### PUT `/api/users/:id`
Atualiza dados de um usuário.

**Autenticação**: Requerida (Admin)

**Request Body:**
```json
{
  "name": "Nome Atualizado",
  "role": "admin"
}
```

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "usuario@exemplo.com",
    "name": "Nome Atualizado",
    "role": "admin"
  }
}
```

---

### DELETE `/api/users/:id`
Remove um usuário do sistema.

**Autenticação**: Requerida (Admin)

**Response (200):**
```json
{
  "success": true,
  "message": "Usuário removido com sucesso"
}
```

---

## 🔍 Status e Saúde

### GET `/api/health`
Verifica o status da API e suas dependências.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-02-05T10:30:00Z",
  "services": {
    "database": "connected",
    "supabase": "connected",
    "aws_s3": "available",
    "vertex_ai": "available"
  },
  "version": "1.0.0"
}
```

---

## 📊 Rate Limiting

A API implementa rate limiting para proteger contra abuso:

- **Requisições por minuto**: 60
- **Requisições por hora**: 1000

Headers de resposta:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1612525200
```

Quando o limite é excedido:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 30
}
```

---

## 🚨 Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 201 | Recurso criado |
| 400 | Requisição inválida |
| 401 | Não autenticado |
| 403 | Sem permissão |
| 404 | Recurso não encontrado |
| 409 | Conflito (ex: email já existe) |
| 429 | Rate limit excedido |
| 500 | Erro interno do servidor |
| 503 | Serviço temporariamente indisponível |

---

## 📝 Formato de Erro Padrão

Todas as respostas de erro seguem este formato:

```json
{
  "success": false,
  "error": "Mensagem de erro legível",
  "code": "ERROR_CODE",
  "details": {
    "campo": "Descrição do problema"
  },
  "timestamp": "2024-02-05T10:30:00Z"
}
```

---

## 🧪 Ambiente de Teste

**Base URL**: `http://localhost:5000`

**Credenciais de Teste:**
```
Email: admin@teste.com
Senha: admin123
```

---

## 📚 Exemplos de Uso

### cURL

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@teste.com","password":"admin123"}'

# Buscar paciente
curl -X GET "http://localhost:5000/api/buscar_paciente?cpf=12345678900" \
  -H "Authorization: Bearer SEU_TOKEN"
```

### JavaScript (Fetch)

```javascript
// Login
const login = async () => {
  const response = await fetch('http://localhost:5000/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: 'admin@teste.com',
      password: 'admin123'
    })
  });
  const data = await response.json();
  return data.token;
};

// Buscar paciente
const buscarPaciente = async (cpf, token) => {
  const response = await fetch(`http://localhost:5000/api/buscar_paciente?cpf=${cpf}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return await response.json();
};
```

### Python (Requests)

```python
import requests

# Login
response = requests.post('http://localhost:5000/api/auth/login', json={
    'email': 'admin@teste.com',
    'password': 'admin123'
})
token = response.json()['token']

# Buscar paciente
response = requests.get(
    'http://localhost:5000/api/buscar_paciente',
    params={'cpf': '12345678900'},
    headers={'Authorization': f'Bearer {token}'}
)
paciente = response.json()
```

---

**Versão da API**: 1.0.0  
**Última atualização**: Fevereiro 2026
