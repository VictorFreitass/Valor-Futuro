import os
import sys

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config.settings import config, db, login_manager, migrate

sys.path.insert(0, os.path.dirname(__file__))


def number_format_filter(value, decimals=0, decimal_sep=',', thousands_sep='.'):
    """Formata um número com separadores de milhares e casas decimais."""
    try:
        value = float(value)
        if decimals == 0:
            return f"{int(value):,}".replace(',', thousands_sep)
        formatted = f"{value:,.{decimals}f}"
        formatted = formatted.replace(',', '#TEMP#')
        formatted = formatted.replace('.', decimal_sep)
        formatted = formatted.replace('#TEMP#', thousands_sep)
        return formatted
    except (ValueError, TypeError):
        return value


def _resolve_config_name(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = (os.environ.get('FLASK_ENV') or '').lower().strip()
    if env in ('production', 'prod'):
        return 'production'
    if env in ('development', 'dev'):
        return 'development'
    # Render injects RENDER=true in its build env
    if os.environ.get('RENDER') or os.environ.get('DYNO'):
        return 'production'
    return 'default'


def create_app(config_name: str | None = None):
    app = Flask(__name__)
    app.config.from_object(config[_resolve_config_name(config_name)])

    # Trust Render/Heroku/Nginx X-Forwarded-* headers so url_for builds https URLs
    # and the rate-limiter sees real client IPs instead of the load balancer.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Serve /static/ via WhiteNoise in production (efficient, sets cache headers).
    if not app.config.get('DEBUG'):
        try:
            from whitenoise import WhiteNoise
            static_root = os.path.join(os.path.dirname(__file__), 'static')
            app.wsgi_app = WhiteNoise(
                app.wsgi_app,
                root=static_root,
                prefix='static/',
                max_age=60 * 60 * 24 * 30,  # 30 days for hashed assets
            )
            uploads_root = app.config.get('UPLOAD_FOLDER')
            if uploads_root and os.path.isdir(uploads_root):
                app.wsgi_app.add_files(uploads_root, prefix='static/uploads/')
        except ImportError:
            app.logger.warning("whitenoise não instalado — static via Flask. pip install whitenoise")

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    login_manager.session_protection = 'strong'
    login_manager.login_message = 'Por favor inicie sessão para aceder ao painel administrativo.'
    login_manager.login_message_category = 'error'

    app.jinja_env.filters['number_format'] = number_format_filter

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return db.session.get(User, int(user_id))

    from routes.main import main as main_blueprint
    from routes.admin import admin as admin_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    with app.app_context():
        db.create_all()
        # Sem admin por defeito — usar `python manage.py create-admin <username>`.

    # Avisar quando se está em produção mas a BD ainda é SQLite — perda de dados
    # garantida em plataformas com filesystem efémero (Render free, Heroku).
    if not app.config.get('DEBUG') and app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        app.logger.warning(
            "AVISO: a aplicação está em modo produção a usar SQLite. "
            "Os dados perder-se-ão em cada redeploy. Define DATABASE_URL "
            "para uma BD PostgreSQL (ex: Render, Neon, Supabase)."
        )

    return app


# Instância de módulo — gunicorn pode chamar `gunicorn app:app` directamente.
# Também é o que `python app.py` usa para o servidor de desenvolvimento.
app = create_app()


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '1') == '1' and not app.config.get('TESTING')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)