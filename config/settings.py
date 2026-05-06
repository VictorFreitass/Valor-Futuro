import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def _resolve_secret_key() -> str:
    key = os.environ.get('SECRET_KEY')
    if key and key != 'dev-secret-key':
        return key
    # Fallback for dev: stable per-machine key in instance/ so sessions survive restarts.
    instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    key_path = os.path.join(instance_dir, 'secret_key.bin')
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            return f.read().decode('latin1')
    generated = secrets.token_urlsafe(64)
    with open(key_path, 'wb') as f:
        f.write(generated.encode('latin1'))
    return generated


def _resolve_database_uri() -> str:
    """Return a SQLAlchemy-compatible DB URI.

    Heroku/Render Postgres returns the legacy `postgres://` scheme which
    SQLAlchemy 2.x rejects. We rewrite to `postgresql://` automatically.
    """
    uri = os.environ.get('DATABASE_URL') or 'sqlite:///valor_futuro.db'
    if uri.startswith('postgres://'):
        uri = 'postgresql://' + uri[len('postgres://'):]
    return uri


_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


class Config:
    SECRET_KEY = _resolve_secret_key()
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Re-check stale connections — important for managed Postgres
        'pool_recycle': 280,
    }
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(_PROJECT_ROOT, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

    # Session hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # In production we expect SECRET_KEY/DATABASE_URL to be set explicitly.
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}