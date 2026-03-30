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

No serviço **automacao-admissao-backend**, configure as mesmas variáveis usadas localmente no `backend/.env`, por exemplo:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `APLIS_BASE_URL`
- `APLIS_USUARIO`
- `APLIS_SENHA`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_BUCKET_NAME`
- `GOOGLE_PROJECT_ID`
- `GOOGLE_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS` (se aplicável)

## 4) Confirmar URL da API no frontend

No serviço **automacao-admissao-frontend**, confira:

- `REACT_APP_API_URL=https://automacao-admissao-backend.onrender.com`

Se o Render gerar outro subdomínio para o backend, atualize esse valor.

## 5) CORS

O backend já está configurado para liberar CORS, então o frontend no Render deve funcionar sem bloqueio de origem.

## 6) Verificação pós deploy

- Backend health: `https://SEU_BACKEND.onrender.com/api/health`
- Frontend: `https://SEU_FRONTEND.onrender.com`
- Teste rápido: buscar requisição e salvar uma admissão

## Observações

- Para OCR/fluxos mais pesados, prefira plano com mais recursos no backend.
- Se usar arquivos locais temporários, valide permissões e limites de disco no serviço.
