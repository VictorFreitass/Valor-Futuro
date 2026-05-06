# Valor Futuro · Imobiliária de Luxo

Plataforma imobiliária premium para o mercado angolano. Construída em Flask, com tema preto-dourado, mapas integrados, autenticação segura e botões directos para WhatsApp / Instagram.

---

## Stack

- **Backend:** Python 3.13 · Flask 3 · SQLAlchemy 2 · Flask-Login · Flask-Migrate
- **Frontend:** HTML5 · CSS (preto-dourado, Cormorant Garamond + Inter) · JS vanilla
- **BD:** SQLite (dev) · PostgreSQL (produção via Render)
- **Produção:** Gunicorn + WhiteNoise + ProxyFix
- **Mapas:** Google Maps embed (sem API key)

---

## Desenvolvimento local

```powershell
# 1. Clonar e entrar na pasta
git clone <repo-url>
cd valor-futuro

# 2. Ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate            # Windows PowerShell
# source .venv/bin/activate         # Linux/macOS

# 3. Dependências
pip install -r requirements.txt

# 4. Configurar variáveis
copy .env.example .env              # Linux: cp .env.example .env
# Edita .env e define DATABASE_URL para Postgres (ver secção abaixo)

# 5. Criar primeiro administrador (interactivo, password com getpass)
python manage.py create-admin valorfuturo_admin

# 6. Correr
python app.py                       # http://127.0.0.1:5000
```

### Base de dados — PostgreSQL

O projecto usa **PostgreSQL** em desenvolvimento e produção (paridade dev/prod).
SQLite continua a funcionar como fallback de emergência, mas o servidor avisa
no log quando é usado em produção.

#### Como obter um PostgreSQL para desenvolvimento

| Opção | Como | Tempo | Custo |
|---|---|---|---|
| **Cloud · Neon** (recomendado) | Conta em https://neon.tech → "Create project" → copiar a connection string | 2 min | grátis (0,5 GB) |
| **Cloud · Supabase** | https://supabase.com → "New project" → Settings → Database → URI | 3 min | grátis (500 MB) |
| **Cloud · Render** | Vai ao Postgres do teu deploy → "External Database URL" (lento mas grátis) | 1 min | grátis (90 dias) |
| **Local Windows** | Instalador oficial em https://www.postgresql.org/download/windows/ | 10 min | grátis |
| **Docker** | `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=local postgres:16` | 1 min | grátis |

Após teres a URL, mete-a no `.env`:

```
DATABASE_URL=postgresql://user:pass@host:5432/database
```

Se ainda tiveres dados em SQLite (`instance/valor_futuro.db`), migra-os com:

```powershell
python migrate_to_postgres.py "postgresql://user:pass@host:5432/database"
```

O script preserva IDs, copia todas as tabelas e ajusta as sequences — pode ser
corrido várias vezes (substitui o conteúdo).

### Comandos úteis

```powershell
# Listar admins
python manage.py list-admins

# Trocar password
python manage.py reset-password valorfuturo_admin

# Eliminar admin
python manage.py delete-admin valorfuturo_admin
```

---

## Estrutura

```
valor-futuro/
├── app.py                  # Factory Flask (gunicorn chama 'app:create_app()')
├── manage.py               # CLI admin (create/reset/delete/list)
├── config/settings.py      # Config dev/prod, sessão, BD, secret key
├── models/                 # User, Property
├── routes/                 # main, admin (login, CRUD, change-password)
├── templates/              # Jinja2 (extends base.html)
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   ├── images/             # logo, favicon, placeholder
│   └── uploads/            # imagens dos imóveis (gitignored)
├── instance/               # SQLite + secret_key.bin (gitignored)
├── requirements.txt
├── Procfile                # web: gunicorn …
├── runtime.txt             # python-3.13.0
├── render.yaml             # Blueprint Render (web + Postgres)
└── .env.example
```

---

## Deploy no Render.com (passo a passo)

### Pré-requisitos
- Repositório Git (GitHub, GitLab ou Bitbucket) com este projecto
- Conta gratuita em https://render.com

### Opção A · Blueprint automático (recomendado)

O ficheiro [`render.yaml`](render.yaml) provisiona web service + Postgres num clique.

1. Faz push do projecto para o teu repo Git.
2. No Render: **New +** → **Blueprint**.
3. Conecta o repo. O Render lê `render.yaml` e mostra os serviços a criar.
4. Clica **Apply** — espera 3-5 minutos pelo build.
5. Depois do primeiro deploy, abre o **Shell** do web service no Render e cria o admin:
   ```bash
   python manage.py create-admin valorfuturo_admin
   ```
6. Visita `https://<o-teu-app>.onrender.com/admin/login`.

### Opção B · Setup manual

Se preferires criar tudo na UI sem Blueprint:

#### B1. Criar a base de dados Postgres
1. **New +** → **PostgreSQL** · plano **Free** · região *Frankfurt*.
2. Copia a `Internal Database URL` (formato `postgres://…`).

#### B2. Criar o web service
1. **New +** → **Web Service** · liga o teu repo Git.
2. Settings:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120`
3. Environment variables:
   | Chave | Valor |
   |---|---|
   | `FLASK_ENV` | `production` |
   | `PYTHON_VERSION` | `3.13.0` |
   | `SECRET_KEY` | (clica *Generate* — chave forte aleatória) |
   | `SESSION_COOKIE_SECURE` | `1` |
   | `DATABASE_URL` | (cola a Internal Database URL do passo B1) |
4. **Create Web Service**. O primeiro build leva ~5 min.
5. Quando ficar online, abre **Shell** → `python manage.py create-admin valorfuturo_admin`.

---

## Particularidades de produção

### Static files
Servidos por **WhiteNoise** directamente do Gunicorn, com cache headers de 30 dias. Não precisa de Nginx separado nem CDN para começar.

### Uploads
A localização é controlada pela env var `UPLOAD_FOLDER` (default: `static/uploads/`).

⚠️ **No plano Free do Render o filesystem é efémero** — todas as imagens carregadas pelo painel admin **desaparecem** em cada deploy/restart.

Soluções:

1. **Persistent disk** (plano Starter, ~$1/mês):
   - No `render.yaml` descomenta o bloco `disk:` e a env var `UPLOAD_FOLDER`.
   - Ou na UI: web service → **Disks** → Add Disk · mount em `/var/data/uploads`, 1 GB.
2. **Storage externo** (Cloudinary, AWS S3, etc.) — recomendado para produção real. Implica alterar o código de upload para usar SDK em vez de filesystem.

### Base de dados
- Postgres do plano Free é apagado após **90 dias** de inactividade.
- Para produção, faz upgrade para **Starter** ($7/mês) → backups automáticos diários, sem expiração.
- O código já lida com a peculiaridade do Render: a string `postgres://...` é reescrita automaticamente para `postgresql://...` (compatibilidade SQLAlchemy 2.x).

### Sessão e segurança
- `SECRET_KEY` é gerada pelo Render (`generateValue: true`) — nunca aparece em logs nem em código.
- Cookies com `Secure`, `HttpOnly`, `SameSite=Lax`.
- `ProxyFix` confia em `X-Forwarded-*` (necessário atrás do load balancer Render).
- Login com rate-limit por IP (5 tentativas / 15 min).
- Passwords com hash **scrypt** (Werkzeug).

---

## Domínio personalizado

1. No web service Render → **Settings** → **Custom Domains** → Add.
2. Adiciona o teu domínio (ex: `valorfuturo.ao`).
3. Configura no teu registrar:
   - `CNAME www` → `<teu-app>.onrender.com`
   - `A @` → IP do Render mostrado na UI
4. Render emite certificado SSL gratuito (Let's Encrypt) automaticamente.

---

## Checklist antes de ir para produção

- [ ] `SECRET_KEY` único e forte definido (não usar default)
- [ ] `SESSION_COOKIE_SECURE=1`
- [ ] `FLASK_ENV=production`
- [ ] Postgres provisionado com backups
- [ ] Disco persistente para uploads (ou storage externo)
- [ ] Admin criado via `manage.py` (sem credenciais hardcoded)
- [ ] Número WhatsApp e Instagram correctos em `templates/base.html`
- [ ] Logo da empresa em `static/images/logo.png` (e variantes geradas)
- [ ] Pelo menos um imóvel real publicado via painel admin
- [ ] Testar `/admin/login`, criar/editar/eliminar imóvel, upload de imagens

---

## Troubleshooting

**Build falha com `psycopg2` em Render**
- Confirma que `psycopg2-binary` está em `requirements.txt` (já está). O `psycopg2` puro precisa de pacotes do sistema.

**`502 Bad Gateway` após deploy**
- Verifica os logs em Render → Logs. Causas comuns: erro de migration ao arrancar, `DATABASE_URL` mal definida, falta de admin user (login devolve 401 mas o site responde 200).

**Static files dão 404**
- Confirma que `whitenoise` está instalado (já em `requirements.txt`). Verifica que `static/` e o seu conteúdo foram commitados.

**Login dá sempre "Credenciais inválidas"**
- Confirma que criaste um utilizador via `manage.py create-admin` no Shell do Render. A BD nasce vazia — não há admin por defeito.

---

## Licença

MIT.
