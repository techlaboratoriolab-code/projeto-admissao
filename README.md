# Sistema de Admissao com OCR

Sistema completo de admissao hospitalar com reconhecimento optico de caracteres (OCR) usando Vertex AI (Gemini).

## Funcionalidades

- **OCR Automatico**: Extracao de dados de documentos medicos usando Vertex AI
- **Interface React**: Frontend moderno e responsivo
- **API Backend**: Flask API para processamento e integracao
- **Banco de Dados**: MySQL para armazenamento de dados
- **Integracao apLIS**: Conexao com sistema apLIS
- **AWS S3**: Armazenamento de imagens
- **ngrok**: Suporte para acesso remoto

## Tecnologias Utilizadas

### Backend
- Python 3.13
- Flask 3.0.0
- Vertex AI (Google Cloud)
- MySQL
- AWS S3
- Boto3

### Frontend
- React
- JavaScript
- CSS3
- HTML5

## Estrutura do Projeto

```
automacao-admissao/
├── backend/
│   ├── api_admissao.py       # API principal
│   ├── logs/                 # Logs da aplicacao
│   └── temp_images/          # Imagens temporarias
├── src/
│   ├── components/           # Componentes React
│   ├── pages/                # Paginas da aplicacao
│   ├── styles/               # Estilos CSS
│   └── config.js             # Configuracoes
├── public/                   # Arquivos publicos
└── node_modules/             # Dependencias Node
```

## Instalacao

### 1. Instalar Dependencias Python

Windows:
```bash
.\instalar_dependencias.bat
```

Linux/Mac:
```bash
pip install -r requirements.txt
```

### 2. Instalar Dependencias Node.js

```bash
npm install
```

### 3. Configurar Variaveis de Ambiente

Crie um arquivo `.env` na pasta `backend/` com:

```env
# Banco de Dados
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=bancodedados

# AWS S3
AWS_ACCESS_KEY_ID=sua_access_key
AWS_SECRET_ACCESS_KEY=sua_secret_key
AWS_REGION=sa-east-1
S3_BUCKET_NAME=aplis2

# Google Cloud (Vertex AI)
GOOGLE_PROJECT_ID=seu-project-id
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=caminho/para/credenciais.json
```

## Executando o Projeto

### 1. Iniciar Backend

```bash
cd backend
python api_admissao.py
```

O backend sera iniciado em `http://localhost:5000`

### 2. Iniciar Frontend

```bash
npm start
```

O frontend sera iniciado em `http://localhost:3000`

### 3. (Opcional) Configurar ngrok para Acesso Remoto

```bash
ngrok http 5000 --domain=seu-dominio.ngrok.dev
```

Atualize `src/config.js` com a URL do ngrok e mude `USE_NGROK` para `true`.

## API Endpoints

### Saude e Teste
- `GET /api/health` - Status do servidor
- `GET /api/admissao/teste` - Testar conexao com apLIS

### Requisicoes
- `GET /api/requisicao/<codigo>` - Buscar requisicao com dados e imagens
- `POST /api/admissao/salvar` - Salvar admissao
- `POST /api/admissao/validar` - Validar dados

### OCR
- `POST /api/ocr/processar` - Processar OCR em imagem
- `POST /api/consolidar-resultados` - Consolidar resultados OCR

### Exames
- `POST /api/exames/buscar-por-nome` - Buscar IDs de exames

### Imagens
- `GET /api/imagem/<filename>` - Servir imagem temporaria

## Configuracao

### Frontend (src/config.js)

```javascript
const NGROK_API_URL = 'https://seu-dominio.ngrok.dev';
const LOCAL_API_URL = 'http://localhost:5000';
const USE_NGROK = false; // true para usar ngrok
```

## Funcionalidades do OCR

O sistema utiliza Vertex AI (Gemini) para extrair automaticamente:

- **Documentos de Identidade**: RG, CNH, OAB, CRM, etc.
- **Carteiras de Convenio**: Nome, matricula, plano
- **Pedidos Medicos**: Paciente, exames, medico, dados clinicos
- **Frascos de Amostra**: Codigo, tipo de material

### Dados Extraidos

- Nome completo do paciente
- CPF (11 digitos)
- RG
- Data de nascimento (formato YYYY-MM-DD)
- Telefone
- Endereco
- Nome do medico e CRM
- Convenio e matricula
- Exames solicitados
- Dados clinicos

## Solucao de Problemas

### Erro "Failed to fetch"

1. Verifique se o backend esta rodando na porta 5000
2. Verifique se o ngrok esta apontando para a porta correta
3. Atualize a URL no `src/config.js`

### Erro de Encoding (Windows)

O sistema ja esta configurado para UTF-8. Se encontrar problemas, verifique a configuracao em `api_admissao.py` linhas 24-29.

### Imagens nao carregam

Verifique:
1. Conexao com AWS S3
2. Credenciais corretas no `.env`
3. Nome do bucket esta correto

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudancas (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## Licenca

Este projeto e proprietario.

## Contato

Para duvidas e suporte, entre em contato com a equipe de desenvolvimento.
