# 📜 Scripts Disponíveis

Guia completo de todos os scripts batch e comandos disponíveis no projeto.

## 🚀 Scripts de Inicialização

### `instalar_tudo.bat`
**Descrição**: Instala todas as dependências do projeto (Node.js + Python)

**Uso**:
```bash
instalar_tudo.bat
```

**O que faz**:
- Instala dependências do frontend (`npm install`)
- Instala dependências do backend (`pip install -r requirements.txt`)
- Cria estrutura de pastas necessárias
- Verifica instalação

---

### `iniciar_sistema.bat`
**Descrição**: Inicia o sistema completo (backend + frontend)

**Uso**:
```bash
iniciar_sistema.bat
```

**O que faz**:
- Abre 2 terminais:
  - Terminal 1: Backend Flask (porta 5000)
  - Terminal 2: Frontend React (porta 3000)
- Aguarda o sistema estar pronto
- Abre o navegador automaticamente

**URLs**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

---

### `iniciar_publico.bat`
**Descrição**: Inicia apenas o frontend

**Uso**:
```bash
iniciar_publico.bat
```

**O que faz**:
- Inicia apenas o React
- Ideal quando o backend já está rodando
- Abre automaticamente no navegador

---

## 👤 Scripts de Usuário

### `criar_admin.bat`
**Descrição**: Cria ou reseta usuário administrador

**Uso**:
```bash
criar_admin.bat
```

**O que faz**:
- Solicita email e senha
- Cria usuário com permissão de admin
- Útil para primeiro acesso ou resetar admin

**Prompt interativo**:
```
Email do admin: admin@exemplo.com
Senha: ********
Confirmar senha: ********
```

---

### `resetar_login.bat`
**Descrição**: Reseta senha de qualquer usuário

**Uso**:
```bash
resetar_login.bat
```

**O que faz**:
- Solicita email do usuário
- Solicita nova senha
- Atualiza senha no banco de dados

---

## 🔧 NPM Scripts (Frontend)

### Desenvolvimento

#### `npm start`
**Descrição**: Inicia o servidor de desenvolvimento

**Uso**:
```bash
npm start
```

**Características**:
- Hot reload ativo
- Abre automaticamente no navegador
- Porta 3000 (padrão)
- Variáveis de ambiente de desenvolvimento

---

#### `npm run build`
**Descrição**: Cria build de produção

**Uso**:
```bash
npm run build
```

**O que faz**:
- Compila o React para produção
- Minifica e otimiza o código
- Gera arquivos na pasta `build/`
- Otimiza imagens e assets

**Saída**: Pasta `build/` pronta para deploy

---

#### `npm test`
**Descrição**: Executa testes (se configurados)

**Uso**:
```bash
npm test
```

---

#### `npm run eject`
**Descrição**: Ejeta as configurações do Create React App

**⚠️ ATENÇÃO**: Operação irreversível! Use apenas se necessário.

---

## 🐍 Scripts Python (Backend)

### API Principal

#### `python backend/api_admissao.py`
**Descrição**: Inicia a API principal

**Uso**:
```bash
cd backend
python api_admissao.py
```

**Porta**: 5000 (padrão)

**Endpoints disponíveis**:
- `/api/buscar_paciente`
- `/api/buscar_requisicao`
- `/api/medicos`
- `/api/instituicoes`
- `/api/convenios`
- etc.

---

#### `python backend/api_auth.py`
**Descrição**: API de autenticação (se separada)

**Uso**:
```bash
cd backend
python api_auth.py
```

---

### Scripts de Administração

#### `python backend/resetar_senha_admin.py`
**Descrição**: Reseta senha de admin via CLI

**Uso**:
```bash
cd backend
python resetar_senha_admin.py
```

**Interativo**:
```python
Email: admin@exemplo.com
Nova senha: ********
Senha atualizada com sucesso!
```

---

### Scripts de Extração de Dados

#### `python backend/extrair_instituicoes.py`
**Descrição**: Extrai instituições do banco para CSV

**Uso**:
```bash
cd backend
python extrair_instituicoes.py
```

**Saída**: `dados/instituicoes_extraidas_YYYYMMDD_HHMMSS.csv`

---

### Scripts de Teste

#### `python backend/testar_busca_paciente.py`
**Descrição**: Testa busca de pacientes

**Uso**:
```bash
cd backend
python testar_busca_paciente.py
```

---

#### `python backend/testar_cache_instituicoes.py`
**Descrição**: Testa sistema de cache

**Uso**:
```bash
cd backend
python testar_cache_instituicoes.py
```

---

#### `python backend/testar_conexao_simples.py`
**Descrição**: Testa conexão com banco de dados

**Uso**:
```bash
cd backend
python testar_conexao_simples.py
```

**Saída esperada**:
```
✅ Conexão com banco estabelecida!
✅ Supabase conectado!
```

---

#### `python backend/verificar_cache_api.py`
**Descrição**: Verifica status do cache da API

**Uso**:
```bash
cd backend
python verificar_cache_api.py
```

---

#### `python backend/verificar_inconsistencia_cpf.py`
**Descrição**: Verifica inconsistências de CPF no banco

**Uso**:
```bash
cd backend
python verificar_inconsistencia_cpf.py
```

---

### Scripts de Listagem

#### `python backend/listar_tabelas.py`
**Descrição**: Lista todas as tabelas do banco

**Uso**:
```bash
cd backend
python listar_tabelas.py
```

**Saída**:
```
Tabelas disponíveis:
- pacientes
- requisicoes
- medicos
- convenios
- instituicoes
```

---

## 🗄️ Scripts SQL

### `promover_admin.sql`
**Descrição**: Promove usuário existente para admin

**Uso no Supabase SQL Editor**:
```sql
-- Substituir o email
UPDATE public.users 
SET role = 'admin' 
WHERE email = 'usuario@exemplo.com';
```

---

### `supabase_disable_email_confirmation.sql`
**Descrição**: Desabilita confirmação de email (desenvolvimento)

**Uso no Supabase SQL Editor**:
```sql
-- Executar no SQL Editor
UPDATE auth.config
SET email_confirm = false;
```

**⚠️ ATENÇÃO**: Use apenas em desenvolvimento!

---

### `supabase_fix_users.sql`
**Descrição**: Corrige estrutura da tabela de usuários

**Uso**:
```sql
-- Criar tabela se não existir
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Habilitar RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
```

---

## 🌐 Scripts de WebService

### `python webservice/webservice.py`
**Descrição**: Inicia webservice de integração

**Uso**:
```bash
cd webservice
python webservice.py
```

---

### `python webservice/teste_api_cpf.py`
**Descrição**: Testa busca por CPF via API

**Uso**:
```bash
cd webservice
python teste_api_cpf.py
```

---

### `python webservice/investigar_metodos_aplis.py`
**Descrição**: Investiga métodos disponíveis no apLIS

**Uso**:
```bash
cd webservice
python investigar_metodos_aplis.py
```

---

## 🔄 Scripts de Backup

Localizados em `backup_scripts/` (não versionados no Git)

### `backup_scripts/testar_banco.bat`
**Descrição**: Testa conexão com banco de dados

### `backup_scripts/testar_conexao_db.py`
**Descrição**: Testa conexão detalhada

### `backup_scripts/iniciar.bat`
**Descrição**: Script antigo de inicialização

---

## ⚙️ Variáveis de Ambiente

### Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:5000
REACT_APP_SUPABASE_URL=https://seu-projeto.supabase.co
REACT_APP_SUPABASE_KEY=sua-chave-publica
```

### Backend (backend/.env)
Ver arquivo `backend/.env.example` para lista completa.

---

## 🛠️ Comandos Úteis

### Limpar Cache

#### Node.js
```bash
# Limpar node_modules
rm -rf node_modules package-lock.json
npm install

# Limpar cache do npm
npm cache clean --force
```

#### Python
```bash
# Limpar __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +

# Limpar .pyc
find . -type f -name "*.pyc" -delete

# Reinstalar dependências
pip install -r backend/requirements.txt --force-reinstall
```

---

### Logs

#### Ver logs do backend
```bash
# Windows
type backend\logs\api_admissao.log

# Linux/Mac
tail -f backend/logs/api_admissao.log
```

#### Limpar logs
```bash
# Windows
del backend\logs\*.log

# Linux/Mac
rm backend/logs/*.log
```

---

### Git

#### Preparar para commit
```bash
# Verificar status
git status

# Adicionar arquivos
git add .

# Commit
git commit -m "feat: descrição da mudança"

# Push
git push origin main
```

#### Criar nova branch
```bash
# Criar e mudar para nova branch
git checkout -b feature/nova-funcionalidade

# Push da nova branch
git push -u origin feature/nova-funcionalidade
```

---

## 📊 Scripts de Monitoramento

### Verificar portas em uso
```bash
# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :3000
lsof -i :5000
```

### Matar processo em porta
```bash
# Windows
taskkill /PID <numero-do-pid> /F

# Linux/Mac
kill -9 <numero-do-pid>
```

---

## 🎯 Fluxo de Trabalho Recomendado

### Primeira vez
```bash
1. instalar_tudo.bat
2. Configurar backend/.env
3. Configurar src/config.js
4. criar_admin.bat
5. iniciar_sistema.bat
```

### Desenvolvimento diário
```bash
1. git pull origin main
2. npm install (se houver mudanças no package.json)
3. iniciar_sistema.bat
4. Desenvolver
5. git add . && git commit -m "mensagem" && git push
```

### Deploy
```bash
1. npm run build
2. Testar build localmente
3. Deploy do frontend (Vercel/Netlify)
4. Deploy do backend (Render/Railway)
5. Configurar variáveis de ambiente
6. Verificar logs e monitoramento
```

---

## 📞 Ajuda

Se um script não funcionar:

1. **Verifique dependências instaladas**
   ```bash
   node --version
   python --version
   npm --version
   pip --version
   ```

2. **Verifique logs de erro**
   - Terminal onde o script foi executado
   - `backend/logs/api_admissao.log`

3. **Verifique variáveis de ambiente**
   - `backend/.env` existe e está configurado
   - `src/config.js` está configurado

4. **Consulte documentação**
   - [README.md](README.md)
   - [INSTALACAO.md](INSTALACAO.md)
   - [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Última atualização**: Fevereiro 2026
