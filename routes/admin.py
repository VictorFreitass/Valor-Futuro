import os
import time
import uuid
from collections import deque
from threading import Lock
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, abort, session,
)
from flask_login import login_user, logout_user, login_required, current_user

from config.settings import db
from models import User, Property

admin = Blueprint('admin', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# In-memory login throttle (per IP). Single-process; for multi-worker deployments
# replace with Redis or Flask-Limiter.
_LOGIN_ATTEMPTS_LOCK = Lock()
_LOGIN_ATTEMPTS: dict[str, deque] = {}
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 15 * 60
MIN_PASSWORD_LEN = 8


def _client_ip() -> str:
    forwarded = request.headers.get('X-Forwarded-For', '')
    return (forwarded.split(',')[0].strip() if forwarded else request.remote_addr) or 'unknown'


def _attempts_remaining(ip: str) -> int:
    now = time.time()
    with _LOGIN_ATTEMPTS_LOCK:
        dq = _LOGIN_ATTEMPTS.setdefault(ip, deque())
        while dq and now - dq[0] > _LOGIN_WINDOW_SECONDS:
            dq.popleft()
        return max(0, _LOGIN_MAX_ATTEMPTS - len(dq))


def _record_failed_attempt(ip: str) -> None:
    with _LOGIN_ATTEMPTS_LOCK:
        _LOGIN_ATTEMPTS.setdefault(ip, deque()).append(time.time())


def _clear_attempts(ip: str) -> None:
    with _LOGIN_ATTEMPTS_LOCK:
        _LOGIN_ATTEMPTS.pop(ip, None)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_uploads(files):
    saved = []
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    for f in files:
        if not f or not f.filename or not allowed_file(f.filename):
            continue
        ext = f.filename.rsplit('.', 1)[1].lower()
        stem = secure_filename(f.filename.rsplit('.', 1)[0]) or 'img'
        unique = f"{stem}-{uuid.uuid4().hex[:8]}.{ext}"
        f.save(os.path.join(upload_dir, unique))
        saved.append(unique)
    return saved


def _delete_image_files(filenames):
    upload_dir = current_app.config['UPLOAD_FOLDER']
    for name in filenames:
        if not name:
            continue
        path = os.path.join(upload_dir, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _read_property_form():
    return {
        'title': (request.form.get('title') or '').strip(),
        'price': float(request.form.get('price') or 0),
        'location': (request.form.get('location') or '').strip(),
        'description': (request.form.get('description') or '').strip(),
        'bedrooms': int(request.form.get('bedrooms') or 0),
        'bathrooms': int(request.form.get('bathrooms') or 0),
        'area': float(request.form.get('area') or 0),
        'property_type': (request.form.get('property_type') or '').strip(),
        'status': (request.form.get('status') or 'para venda').strip(),
        'is_featured': bool(request.form.get('is_featured')),
    }


@admin.route('/', methods=['GET'])
@admin.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('admin_panel.html', properties=properties)


@admin.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        ip = _client_ip()
        remaining = _attempts_remaining(ip)
        if remaining <= 0:
            flash('Demasiadas tentativas falhadas. Tente novamente daqui a alguns minutos.', 'error')
            return render_template('admin_login.html'), 429

        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            _clear_attempts(ip)
            session.clear()  # mitigate session fixation — reset before login
            session.permanent = True
            login_user(user, remember=False)
            return redirect(url_for('admin.dashboard'))

        _record_failed_attempt(ip)
        # Generic message — não revela se o utilizador existe.
        flash('Credenciais inválidas.', 'error')

    return render_template('admin_login.html')


@admin.route('/logout')
@login_required
def logout_view():
    logout_user()
    session.clear()
    flash('Sessão terminada com sucesso.', 'success')
    return redirect(url_for('main.index'))


@admin.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password') or ''
        new = request.form.get('new_password') or ''
        confirm = request.form.get('confirm_password') or ''

        if not current_user.check_password(current):
            flash('A password actual está incorrecta.', 'error')
            return render_template('change_password.html')

        if len(new) < MIN_PASSWORD_LEN:
            flash(f'A nova password tem de ter pelo menos {MIN_PASSWORD_LEN} caracteres.', 'error')
            return render_template('change_password.html')

        if new == current:
            flash('A nova password tem de ser diferente da actual.', 'error')
            return render_template('change_password.html')

        if new != confirm:
            flash('A confirmação não coincide com a nova password.', 'error')
            return render_template('change_password.html')

        current_user.set_password(new)
        db.session.commit()
        # Forçar novo login após alterar password
        logout_user()
        session.clear()
        flash('Password actualizada. Faça login com as novas credenciais.', 'success')
        return redirect(url_for('admin.login'))

    return render_template('change_password.html')


@admin.route('/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        try:
            data = _read_property_form()
        except ValueError:
            flash('Verifique os campos numéricos (preço, área, quartos).', 'error')
            return redirect(url_for('admin.add_property'))

        images = _save_uploads(request.files.getlist('images'))

        new_property = Property(
            **data,
            images=','.join(images) if images else None,
        )
        db.session.add(new_property)
        db.session.commit()
        flash(f'Imóvel "{new_property.title}" adicionado com sucesso.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('add_property.html')


@admin.route('/property/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_property(id):
    property_obj = db.session.get(Property, id) or abort(404)

    if request.method == 'POST':
        try:
            data = _read_property_form()
        except ValueError:
            flash('Verifique os campos numéricos.', 'error')
            return redirect(url_for('admin.edit_property', id=id))

        for key, value in data.items():
            setattr(property_obj, key, value)

        new_files = request.files.getlist('images')
        if any(f and f.filename for f in new_files):
            new_images = _save_uploads(new_files)
            if new_images:
                existing = property_obj.images.split(',') if property_obj.images else []
                property_obj.images = ','.join(existing + new_images)

        db.session.commit()
        flash('Imóvel atualizado com sucesso.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('edit_property.html', property=property_obj)


@admin.route('/property/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_property(id):
    property_obj = db.session.get(Property, id) or abort(404)
    if property_obj.images:
        _delete_image_files(property_obj.images.split(','))
    db.session.delete(property_obj)
    db.session.commit()
    flash('Imóvel eliminado.', 'success')
    return redirect(url_for('admin.dashboard'))
