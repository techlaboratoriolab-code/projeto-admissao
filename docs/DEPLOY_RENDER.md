# Deploy no Render (Frontend + Backend)

Este projeto está preparado para deploy centralizado no Render usando o arquivo [render.yaml](../render.yaml).

## 1) Pré-requisitos

- Repositório no GitHub atualizado
- Conta no Render
- Variáveis sensíveis do backend em mãos (Supabase, MySQL/apLIS, AWS, Google)

## 2) Criar os serviços via Blueprint

1. No Render: **New +** → **Blueprint**
2. Conecte seu repositório
3. O Render vai detectar o arquivo `render.yaml`
4. Crie os 2 serviços:
   - `automacao-admissao-backend`
   - `automacao-admissao-frontend`

## 3) Configurar variáveis de ambiente (backend)

No serviço **automacao-admissao-backend**, configure estas variáveis.

### Obrigatórias para operação principal

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `APLIS_USUARIO`
- `APLIS_SENHA`
- `JWT_SECRET`

### Obrigatórias conforme recursos habilitados

- Consulta CPF: `CPF_API_TOKEN`
- Upload/arquivos S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`
- OCR Vertex AI: `GOOGLE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`

### Opcionais (com default no código)

- `APLIS_BASE_URL` (default: `https://lab.aplis.inf.br/api/integracao.php`)
- `AWS_REGION` (default: `sa-east-1`)
- `GOOGLE_LOCATION` (default: `us-central1`)

### Bloco copy/paste (nomes das chaves)

Use este bloco para conferência rápida no painel do Render:

```env
SUPABASE_URL=
SUPABASE_KEY=
DB_HOST=
DB_USER=
DB_PASSWORD=
DB_NAME=
APLIS_BASE_URL=https://lab.aplis.inf.br/api/integracao.php
APLIS_USUARIO=
APLIS_SENHA=
JWT_SECRET=
CPF_API_TOKEN=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=sa-east-1
S3_BUCKET_NAME=
GOOGLE_PROJECT_ID=
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=
```

> Observação: `GOOGLE_APPLICATION_CREDENTIALS` deve apontar para um caminho de arquivo no container (ex.: `/etc/secrets/google-credentials.json`).

## 4) Configurar variáveis de ambiente (frontend)

No serviço **automacao-admissao-frontend**, configure:

- `REACT_APP_API_URL=https://automacao-admissao-backend.onrender.com`
- `REACT_APP_SUPABASE_URL`
- `REACT_APP_SUPABASE_ANON_KEY`
- `REACT_APP_SUPABASE_SERVICE_KEY`

Se o Render gerar outro subdomínio para o backend, atualize esse valor.

Bloco rápido:

```env
REACT_APP_API_URL=https://automacao-admissao-backend.onrender.com
REACT_APP_SUPABASE_URL=
REACT_APP_SUPABASE_ANON_KEY=
REACT_APP_SUPABASE_SERVICE_KEY=
```

## 5) CORS

O backend já está configurado para liberar CORS, então o frontend no Render deve funcionar sem bloqueio de origem.

## 6) Verificação pós deploy

- Backend health: `https://SEU_BACKEND.onrender.com/api/health`
- Frontend: `https://SEU_FRONTEND.onrender.com`
- Teste rápido: buscar requisição e salvar uma admissão

## Observações

- Para OCR/fluxos mais pesados, prefira plano com mais recursos no backend.
- Se usar arquivos locais temporários, valide permissões e limites de disco no serviço.
