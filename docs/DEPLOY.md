# Guia de Deploy - Sistema de Automação de Admissão

Este guia fornece instruções detalhadas para fazer o deploy do sistema em produção.

## 📋 Índice

- [Pré-requisitos](#pré-requisitos)
- [Deploy do Frontend](#deploy-do-frontend)
- [Deploy do Backend](#deploy-do-backend)
- [Configuração de Domínio](#configuração-de-domínio)
- [SSL/HTTPS](#sslhttps)
- [Monitoramento](#monitoramento)
- [Backup](#backup)

---

## 🎯 Pré-requisitos

Antes de fazer o deploy, certifique-se de ter:

- [ ] Conta na plataforma de deploy escolhida
- [ ] Domínio configurado (ex: seusite.com)
- [ ] Credenciais de produção (Supabase, AWS, GCP)
- [ ] Variáveis de ambiente configuradas
- [ ] Código testado e funcionando localmente

---

## 🌐 Deploy do Frontend (React)

### Opção 1: Vercel (Recomendado)

#### Por que Vercel?
- ✅ Deploy automático via Git
- ✅ CDN global
- ✅ SSL gratuito
- ✅ Suporte nativo para React
- ✅ Domínio gratuito (.vercel.app)

#### Passo a Passo

1. **Instalar Vercel CLI**
```bash
npm install -g vercel
```

2. **Login no Vercel**
```bash
vercel login
```

3. **Deploy**
```bash
# No diretório raiz do projeto
vercel

# Para produção
vercel --prod
```

4. **Configurar Variáveis de Ambiente**
   - Vá para o dashboard do Vercel
   - Selecione seu projeto
   - Settings → Environment Variables
   - Adicione:
     - `REACT_APP_API_URL`: URL do backend
     - `REACT_APP_SUPABASE_URL`: URL do Supabase
     - `REACT_APP_SUPABASE_KEY`: Chave pública do Supabase

5. **Configurar vercel.json** (opcional)
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "build",
  "devCommand": "npm start",
  "routes": [
    {
      "src": "/static/(.*)",
      "headers": { "cache-control": "public, max-age=31536000, immutable" }
    },
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ]
}
```

#### Deploy Automático via Git

1. Conecte seu repositório GitHub ao Vercel
2. Cada push para `main` fará deploy automático
3. Pull Requests geram preview deploys

---

### Opção 2: Netlify

#### Passo a Passo

1. **Build do projeto**
```bash
npm run build
```

2. **Deploy via Netlify CLI**
```bash
# Instalar CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy

# Deploy para produção
netlify deploy --prod
```

3. **Deploy via Dashboard**
   - Acesse https://app.netlify.com/
   - Arraste a pasta `build/` para o dashboard
   - Configure variáveis de ambiente
   - Configure domínio customizado

4. **Configurar netlify.toml**
```toml
[build]
  command = "npm run build"
  publish = "build"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/static/*"
  [headers.values]
    cache-control = "public, max-age=31536000, immutable"
```

---

### Opção 3: AWS S3 + CloudFront

#### Passo a Passo

1. **Criar Bucket S3**
```bash
aws s3 mb s3://seu-bucket-frontend --region us-east-1
```

2. **Configurar bucket para hosting**
```bash
aws s3 website s3://seu-bucket-frontend --index-document index.html --error-document index.html
```

3. **Build e Upload**
```bash
npm run build
aws s3 sync build/ s3://seu-bucket-frontend --delete
```

4. **Criar distribuição CloudFront**
   - Origin: Bucket S3
   - Default Root Object: index.html
   - Error Pages: Redirecionar 404 para /index.html

---

## 🐍 Deploy do Backend (Flask)

### Opção 1: Render (Recomendado)

#### Por que Render?
- ✅ Deploy automático via Git
- ✅ SSL gratuito
- ✅ Fácil configuração
- ✅ Plano gratuito disponível
- ✅ Suporte nativo para Python

#### Passo a Passo

1. **Criar render.yaml**
```yaml
services:
  - type: web
    name: automacao-admissao-api
    env: python
    region: oregon
    buildCommand: cd backend && pip install -r requirements.txt
    startCommand: cd backend && python api_admissao.py
    envVars:
      - key: PORT
        value: 10000
      - key: FLASK_ENV
        value: production
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: DB_HOST
        sync: false
      - key: DB_USER
        sync: false
      - key: DB_PASSWORD
        sync: false
      - key: DB_NAME
        sync: false
```

2. **Modificar api_admissao.py**
```python
# No final do arquivo
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
```

3. **Deploy via Dashboard**
   - Acesse https://dashboard.render.com/
   - New → Web Service
   - Conecte seu repositório GitHub
   - Configure variáveis de ambiente
   - Deploy

---

### Opção 2: Railway

#### Passo a Passo

1. **Instalar Railway CLI**
```bash
npm install -g @railway/cli
```

2. **Login e Inicializar**
```bash
railway login
railway init
```

3. **Deploy**
```bash
railway up
```

4. **Configurar Variáveis de Ambiente**
```bash
railway variables set SUPABASE_URL="https://..."
railway variables set SUPABASE_KEY="..."
railway variables set DB_HOST="..."
# ... etc
```

---

### Opção 3: Heroku

#### Passo a Passo

1. **Criar Procfile**
```
web: cd backend && python api_admissao.py
```

2. **Criar runtime.txt**
```
python-3.11.0
```

3. **Deploy via Git**
```bash
# Login
heroku login

# Criar app
heroku create seu-app-name

# Adicionar variáveis de ambiente
heroku config:set SUPABASE_URL="https://..."
heroku config:set SUPABASE_KEY="..."

# Deploy
git push heroku main
```

---

### Opção 4: VPS (Linux Server)

#### Passo a Passo

1. **Conectar ao servidor**
```bash
ssh usuario@seu-servidor.com
```

2. **Instalar dependências**
```bash
sudo apt update
sudo apt install python3 python3-pip nginx supervisor
```

3. **Clonar projeto**
```bash
cd /var/www
git clone https://github.com/seu-usuario/automacao-admissao.git
cd automacao-admissao/backend
pip3 install -r requirements.txt
```

4. **Configurar Gunicorn**
```bash
pip3 install gunicorn
```

5. **Criar arquivo de serviço**
```bash
sudo nano /etc/supervisor/conf.d/api-admissao.conf
```

```ini
[program:api-admissao]
directory=/var/www/automacao-admissao/backend
command=/usr/bin/python3 api_admissao.py
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/api-admissao.err.log
stdout_logfile=/var/log/api-admissao.out.log
```

6. **Configurar Nginx**
```bash
sudo nano /etc/nginx/sites-available/api-admissao
```

```nginx
server {
    listen 80;
    server_name api.seudominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. **Ativar configuração**
```bash
sudo ln -s /etc/nginx/sites-available/api-admissao /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo supervisorctl reread
sudo supervisorctl update
```

---

## 🌍 Configuração de Domínio

### Frontend

1. **Adicionar domínio customizado**
   - Vercel/Netlify: Dashboard → Domains → Add Custom Domain
   - Digite: `app.seudominio.com`

2. **Configurar DNS**
   - Adicione registro CNAME:
     - Nome: `app`
     - Valor: `seu-projeto.vercel.app`
     - TTL: 3600

### Backend

1. **Adicionar domínio**
   - Configure: `api.seudominio.com`

2. **Configurar DNS**
   - Adicione registro CNAME:
     - Nome: `api`
     - Valor: URL do serviço (Render/Railway)
     - TTL: 3600

---

## 🔒 SSL/HTTPS

### Automático (Vercel/Netlify/Render)

SSL é configurado automaticamente ao adicionar domínio customizado.

### Manual (VPS com Let's Encrypt)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d api.seudominio.com

# Renovação automática
sudo certbot renew --dry-run
```

---

## 📊 Monitoramento

### Sentry (Erros)

1. **Instalar**
```bash
# Frontend
npm install @sentry/react

# Backend
pip install sentry-sdk[flask]
```

2. **Configurar Frontend**
```javascript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "https://...@sentry.io/...",
  environment: process.env.NODE_ENV
});
```

3. **Configurar Backend**
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="https://...@sentry.io/...",
    integrations=[FlaskIntegration()],
    environment="production"
)
```

### Uptime Monitoring

Use serviços como:
- **UptimeRobot**: https://uptimerobot.com/
- **Pingdom**: https://www.pingdom.com/
- **StatusCake**: https://www.statuscake.com/

---

## 💾 Backup

### Banco de Dados (Supabase)

```bash
# Backup automático via dashboard
# Settings → Database → Backups

# Backup manual via CLI
supabase db dump -f backup.sql
```

### Arquivos (AWS S3)

```bash
# Backup automático com versionamento
aws s3api put-bucket-versioning \
  --bucket seu-bucket \
  --versioning-configuration Status=Enabled

# Backup manual
aws s3 sync s3://seu-bucket ./backup
```

---

## ✅ Checklist de Deploy

### Antes do Deploy

- [ ] Todos os testes passam
- [ ] Código revisado e aprovado
- [ ] Variáveis de ambiente configuradas
- [ ] Build funciona sem erros
- [ ] Dependências atualizadas
- [ ] Documentação atualizada

### Durante o Deploy

- [ ] Deploy do backend realizado
- [ ] Deploy do frontend realizado
- [ ] Variáveis de ambiente verificadas
- [ ] SSL configurado
- [ ] Domínios apontando corretamente

### Após o Deploy

- [ ] Teste de smoke (funcionalidades principais)
- [ ] Verificar logs de erro
- [ ] Configurar monitoramento
- [ ] Configurar backup
- [ ] Notificar equipe

---

## 🐛 Troubleshooting

### Build Failed

**Problema**: Erro durante o build

**Solução**:
- Verifique logs de build
- Teste localmente: `npm run build`
- Verifique variáveis de ambiente
- Verifique versão do Node.js

### CORS Error

**Problema**: Erro de CORS no frontend

**Solução**:
```python
# backend/api_admissao.py
CORS(app, origins=[
    'https://seu-frontend.vercel.app',
    'https://app.seudominio.com'
])
```

### 502 Bad Gateway

**Problema**: Backend não responde

**Solução**:
- Verifique se o backend está rodando
- Verifique logs do servidor
- Verifique configuração do proxy/nginx
- Verifique porta configurada

---

## 📞 Suporte

Se encontrar problemas durante o deploy:

1. Consulte os logs
2. Verifique a documentação da plataforma
3. Abra uma issue no GitHub
4. Entre em contato com a equipe

---

**Boa sorte com o deploy! 🚀**
