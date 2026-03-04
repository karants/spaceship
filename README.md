# Spaceship

A personal website with a photography portfolio and identity page, wrapped in a dark space-inspired aesthetic — twinkling stars, gold accents, Cormorant Garamond serif, Courier Prime monospace.

**Public pages:** Launch Pad, Mission Log, Our Earth
**Control panel:** `/groundstation` — manage content and gallery

---

## Architecture

```
spaceship/
├── launch.py                   # Entry point (dev & production)
├── keygen.py                   # CLI to hash & store your access key
├── config.py                   # Configuration classes
├── requirements.txt            # Python dependencies (4 packages)
├── .env.example                # Environment variable template
├── .gitignore
├── instance/                   # Database + key file (auto-created, gitignored)
│   ├── spaceship.db
│   └── access.key
├── app/
│   ├── __init__.py             # App factory (launch function)
│   ├── database.py             # OOP models (Database, MissionLogModel, EarthPhotoModel)
│   ├── security.py             # CSRF, sanitisation, file-based auth, headers
│   ├── storage.py              # Storage abstraction (LocalStorage / CloudStorage)
│   ├── blueprints/
│   │   ├── voyage.py           # Public routes (launchpad, mission_log, our_earth)
│   │   └── groundstation.py    # Control panel routes (/groundstation/*)
│   ├── static/
│   │   ├── css/spaceship.css   # All styles
│   │   ├── js/spaceship.js     # Stars, nav, photo protection
│   │   └── uploads/            # Local image fallback (gitignored)
│   └── templates/
│       ├── base.html           # Public base layout
│       ├── voyage/             # Launch Pad, Mission Log, Our Earth
│       └── groundstation/      # Login, Command Deck, forms
```

---

## Why File-Based Key Authentication?

Environment variables are visible in process listings (`/proc/*/environ`), shell history, CI logs, and hosting dashboards.  Spaceship takes a different approach:

1. You run `python keygen.py` and type your key (hidden input, like `passwd`)
2. The key is salted and SHA-256 hashed, then written to `instance/access.key`
3. The plaintext key is **never stored anywhere** — not in env vars, not in code, not in config
4. At login time, the submitted key is hashed with the same salt and compared using `hmac.compare_digest()` (timing-safe)
5. The key file has `chmod 600` (owner-only read/write)

This means even if someone accesses your server's environment or config files, they see only a salted hash — not your actual key.

---

## Free Image Storage with Cloudinary

Cloudinary's free tier gives you **25 GB storage** and **25 GB bandwidth/month** — more than enough for a personal photography portfolio.  When Cloudinary credentials are configured, all uploads go to their CDN.  Without credentials, images fall back to local disk storage.

### Setting Up Cloudinary (5 minutes)

1. Go to [cloudinary.com](https://cloudinary.com) and create a free account
2. From the Dashboard, copy your **Cloud Name**, **API Key**, and **API Secret**
3. Add them to your `.env` file:
   ```
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=123456789012345
   CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwx
   ```

That's it — the app detects the credentials automatically and switches to cloud storage.

---

## Local Development Setup (Windows + WSL Ubuntu)

### 1. Open WSL Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
python3 --version   # should be 3.11+
sudo apt install -y python3-pip python3-venv git
```

### 2. Get the Project

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/spaceship.git
cd spaceship
```

### 3. Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Generate Your Access Key

```bash
python keygen.py
```

You'll be prompted to type and confirm your key.  The salted hash is stored in `instance/access.key`.

### 6. Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in `SECRET_KEY` (run `python3 -c "import secrets; print(secrets.token_hex(32))"` to generate one) and optionally your Cloudinary credentials.

### 7. Run

```bash
export $(cat .env | xargs)
python launch.py
```

- Public site: `http://localhost:5000`
- Ground Station: `http://localhost:5000/groundstation`

### 8. Open in VS Code

```bash
code .
```

Install the Python and WSL extensions when prompted.

---

## Deployment with Render (Free)

### 1. Push to GitHub

```bash
cd ~/spaceship
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/spaceship.git
git branch -M main
git push -u origin main
```

### 2. Set Up Render

1. Go to [render.com](https://render.com) → sign up with GitHub
2. **New** → **Web Service** → connect your repo
3. Configure:
   - **Name:** spaceship
   - **Branch:** main
   - **Build Command:** `pip install -r requirements.txt && python keygen_render.py`
   - **Start Command:** `gunicorn launch:app`
4. Add environment variables:
   - `SECRET_KEY` → your generated key
   - `FLASK_ENV` → `production`
   - `CLOUDINARY_CLOUD_NAME` → from Cloudinary dashboard
   - `CLOUDINARY_API_KEY` → from Cloudinary dashboard
   - `CLOUDINARY_API_SECRET` → from Cloudinary dashboard
   - `SPACESHIP_ACCESS_KEY` → your chosen access key (used only during build to generate the hash file)

### 3. Create the Render Build Script

Since Render can't run interactive `keygen.py`, create this helper:

```python
# keygen_render.py — non-interactive keygen for CI/CD
import hashlib, os, secrets

key = os.environ.get("SPACESHIP_ACCESS_KEY", "")
if not key:
    print("SPACESHIP_ACCESS_KEY not set, skipping keygen")
    exit(0)

os.makedirs("instance", exist_ok=True)
salt = secrets.token_hex(16)
digest = hashlib.sha256((salt + key).encode()).hexdigest()
with open("instance/access.key", "w") as f:
    f.write(f"{salt}:{digest}\n")
os.chmod("instance/access.key", 0o600)
print("Access key hash generated for production.")
```

### 4. Connect Your GoDaddy Domain

1. In Render → your service → **Settings** → **Custom Domains** → add your domain
2. In GoDaddy → **DNS Management**:
   - Add a **CNAME** record pointing to your Render URL
3. Render auto-provisions a free SSL certificate

---

## Security Checklist

| Protection | Implementation |
|---|---|
| **Authentication** | Salted SHA-256 hash stored in file with `chmod 600`; timing-safe comparison via `hmac.compare_digest()` |
| **CSRF** | Per-session token on every form; validated server-side before any mutation |
| **XSS** | All user input HTML-escaped via `html.escape()` before database storage |
| **SQL Injection** | Every query uses parameterised placeholders (`?`); zero string concatenation |
| **Path Traversal** | Uploaded filenames replaced with random SHA-256 hashes |
| **Security Headers** | X-Content-Type-Options, X-Frame-Options DENY, CSP, Referrer-Policy, Permissions-Policy |
| **Photo Protection** | Right-click blocked, drag disabled, transparent overlay, PrintScreen deterrent, `pointer-events: none` on images |
| **Session** | HttpOnly, SameSite=Lax, Secure flag in production |
| **Upload Validation** | Extension whitelist (png/jpg/jpeg/webp/gif), 16 MB limit |
| **Dependencies** | Only 4 packages: Flask, Werkzeug, gunicorn, cloudinary |

---

## Adding New Sections

The codebase is modular — here's the pattern for adding a new page:

1. **Model:** Add a new class in `app/database.py` and create its table in `init_schema()`
2. **Route:** Add a new function in `app/blueprints/voyage.py` (public) or `groundstation.py` (control panel)
3. **Template:** Create a new `.html` file in the appropriate `templates/` subfolder
4. **Navigation:** Add a link in `base.html` nav drawer
5. **Register:** If it's a new blueprint, register it in `app/__init__.py`

---

## Route Map

| URL | Blueprint | Description |
|---|---|---|
| `/` | voyage | Launch Pad (landing page) |
| `/mission-log` | voyage | Identity / about page |
| `/our-earth` | voyage | Photography gallery |
| `/groundstation/` | groundstation | Login |
| `/groundstation/command-deck` | groundstation | Dashboard |
| `/groundstation/mission-log/edit` | groundstation | Edit identity section |
| `/groundstation/gallery/add` | groundstation | Upload new photo |
| `/groundstation/gallery/<id>/edit` | groundstation | Edit photo |
| `/groundstation/gallery/<id>/delete` | groundstation | Remove photo |
| `/groundstation/logout` | groundstation | End session |
