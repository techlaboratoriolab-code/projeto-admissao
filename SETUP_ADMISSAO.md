# Sistema de Admissão - Guia de Instalação e Uso

Sistema completo de admissão de pacientes integrado com apLIS.

---

## 📋 Estrutura do Sistema

```
automação admissao/
├── backend/
│   ├── api_admissao.py       # API Flask
│   └── requirements.txt      # Dependências Python
├── src/
│   ├── pages/
│   │   └── AdmissionView.jsx # Interface de admissão
│   └── styles/
│       └── AdmissionView.css # Estilos
├── package.json              # Dependências Node
└── README.md
```

---

## 🚀 Instalação

### 1. Backend (Python/Flask)

```bash
# Navegar para a pasta backend
cd "C:\Users\Windows 11\Desktop\automação admissao\backend"

# Instalar dependências
pip install -r requirements.txt
```

### 2. Frontend (React)

```bash
# Navegar para a raiz do projeto
cd "C:\Users\Windows 11\Desktop\automação admissao"

# Se ainda não instalou as dependências React
npm install
```

---

## ▶️ Executar o Sistema

### Opção 1: Executar Backend e Frontend Separadamente

**Terminal 1 - Backend:**
```bash
cd "C:\Users\Windows 11\Desktop\automação admissao\backend"
python api_admissao.py
```

Servidor iniciará em: `http://localhost:5000`

**Terminal 2 - Frontend:**
```bash
cd "C:\Users\Windows 11\Desktop\automação admissao"
npm start
```

Interface abrirá em: `http://localhost:3000`

### Opção 2: Script de Inicialização (Recomendado)

Crie um arquivo `iniciar.bat`:

```batch
@echo off
echo ========================================
echo   INICIANDO SISTEMA DE ADMISSAO
echo ========================================

start cmd /k "cd backend && python api_admissao.py"
timeout /t 3 >nul
start cmd /k "npm start"

echo.
echo Sistema iniciado!
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
```

Execute: `iniciar.bat`

---

## 🎯 Como Usar

### 1. Acessar a Interface

Abra o navegador em `http://localhost:3000`

A página inicial será a tela de **Nova Admissão**.

### 2. Preencher Formulário

**Dados Obrigatórios:**
- ID Laboratório (padrão: 1)
- ID Unidade (padrão: 1)
- ID Paciente
- Data de Coleta
- ID Convênio
- ID Fonte Pagadora
- ID Médico
- ID Local Origem
- ID Exame Principal
- Exames Convênio (IDs separados por vírgula)

**Dados Opcionais:**
- Código Requisição (para atualizar existente)
- Número da Guia
- Dados Clínicos

### 3. Validar Dados

Clique em **"Validar Dados"** para verificar se os dados estão corretos antes de salvar.

### 4. Salvar Admissão

Clique em **"Salvar Admissão"**.

**Se sucesso:**
- Mensagem verde com código da requisição
- `"Admissão salva com sucesso! Código: 0200050767001"`

**Se erro:**
- Mensagem vermelha com descrição do erro

---

## 🔧 Endpoints da API

### POST `/api/admissao/salvar`
Salva ou atualiza uma admissão.

**Body:**
```json
{
  "idLaboratorio": 1,
  "idUnidade": 1,
  "idPaciente": 87388,
  "dtaColeta": "2025-12-19",
  "idConvenio": 1095,
  "idLocalOrigem": 1,
  "idFontePagadora": 1001,
  "idMedico": 1,
  "idExame": 49,
  "examesConvenio": [49],
  "numGuia": "123456789",
  "dadosClinicos": "Informações clínicas..."
}
```

**Resposta (sucesso):**
```json
{
  "sucesso": 1,
  "mensagem": "Admissão salva com sucesso!",
  "codRequisicao": "0200050767001",
  "dados": { ... }
}
```

### POST `/api/admissao/validar`
Valida dados antes de salvar.

**Resposta:**
```json
{
  "valido": true,
  "erros": [],
  "avisos": ["Número da guia não informado"]
}
```

### GET `/api/health`
Verifica status do servidor.

### GET `/api/admissao/teste`
Testa conexão com apLIS.

---

## 📱 Navegação

A interface possui 4 páginas acessíveis pelo menu superior:

- **Nova Admissão** - Formulário de admissão
- **Pedido Médico** - Visualização de pedidos
- **Laudo** - Visualização de laudos
- **Resultado** - Visualização de resultados

---

## 🐛 Troubleshooting

### Backend não inicia

**Erro:** `ModuleNotFoundError: No module named 'flask'`

**Solução:**
```bash
pip install flask flask-cors requests
```

### Frontend não conecta ao backend

**Erro:** `Failed to fetch` ou `Network error`

**Verificar:**
1. Backend está rodando? `http://localhost:5000/api/health`
2. CORS habilitado? (já está no código)
3. Firewall bloqueando porta 5000?

### Erro ao salvar admissão

**Mensagem:** `Campos obrigatórios faltando`

**Solução:** Preencher todos os campos marcados com *

**Mensagem:** `Timeout ao conectar com apLIS`

**Verificar:**
1. Internet conectada?
2. apLIS está online?
3. Testar: `http://localhost:5000/api/admissao/teste`

---

## 📊 Exemplo Completo

### 1. Iniciar Sistema
```bash
# Terminal 1
cd backend
python api_admissao.py

# Terminal 2
npm start
```

### 2. Acessar Interface
`http://localhost:3000/admissao`

### 3. Preencher Formulário
```
ID Laboratório: 1
ID Unidade: 1
ID Paciente: 87388
Data de Coleta: 2025-12-19
ID Convênio: 1095
ID Fonte Pagadora: 1001
ID Médico: 1
ID Local Origem: 1
ID Exame: 49
Exames Convênio: 49, 50, 51
Número da Guia: 123456789
Dados Clínicos: Paciente com...
```

### 4. Validar
Clique em "Validar Dados" → Mensagem verde "Dados válidos!"

### 5. Salvar
Clique em "Salvar Admissão" → Mensagem "Admissão salva com sucesso! Código: 0200050767001"

---

## 🔐 Segurança

**Credenciais apLIS** estão hardcoded no backend:
- `backend/api_admissao.py` linhas 10-12

**Para produção:**
1. Mover credenciais para variáveis de ambiente
2. Usar arquivo `.env`
3. Adicionar autenticação na API Flask

---

## 🎨 Personalização

### Alterar cores do tema

Editar `src/styles/AdmissionView.css`:
```css
/* Gradiente principal */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Alterar para: */
background: linear-gradient(135deg, #sua-cor-1 0%, #sua-cor-2 100%);
```

### Adicionar campos no formulário

1. Adicionar no `formData` em `AdmissionView.jsx`
2. Criar input no JSX
3. Campo será enviado automaticamente

---

## 📝 Logs e Debug

### Backend
Logs aparecem no terminal do Flask:
```
Status Code: 200
{
  "ver": 1,
  "cmd": "admissaoSalvar",
  "dat": { ... }
}
```

### Frontend
Console do navegador (F12):
```javascript
console.log('Dados enviados:', dados);
console.log('Resposta:', result);
```

---

## ✅ Checklist de Funcionamento

- [ ] Backend rodando em `http://localhost:5000`
- [ ] Frontend rodando em `http://localhost:3000`
- [ ] `/api/health` retorna `status: online`
- [ ] `/api/admissao/teste` retorna `conexao_ok: true`
- [ ] Formulário carrega sem erros
- [ ] Validação funciona
- [ ] Salvamento funciona
- [ ] Mensagens de sucesso/erro aparecem

---

## 📞 Suporte

Sistema desenvolvido para integração com apLIS.

**Arquivos principais:**
- Backend: `backend/api_admissao.py`
- Frontend: `src/pages/AdmissionView.jsx`
- Estilos: `src/styles/AdmissionView.css`

**Rotas:**
- `/admissao` - Nova admissão
- `/pedido-medico` - Pedido médico
- `/laudo` - Laudo
- `/resultado-exame` - Resultado

---

**Versão:** 1.0
**Data:** 31/12/2024
