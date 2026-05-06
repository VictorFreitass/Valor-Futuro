"""Admin management CLI for Valor Futuro.

Uso:
  python manage.py create-admin <username>
  python manage.py reset-password <username>
  python manage.py delete-admin <username>
  python manage.py list-admins

A password é lida via getpass — não fica visível no terminal nem no histórico.
"""
import sys
import getpass

from app import create_app
from config.settings import db
from models import User


MIN_PASSWORD_LEN = 8


def _read_new_password() -> str:
    while True:
        pw = getpass.getpass("Nova password: ")
        if len(pw) < MIN_PASSWORD_LEN:
            print(f"Password tem de ter pelo menos {MIN_PASSWORD_LEN} caracteres.")
            continue
        confirm = getpass.getpass("Confirme a password: ")
        if pw != confirm:
            print("As passwords não coincidem. Tente novamente.\n")
            continue
        return pw


def _usage_and_exit(code: int = 1) -> None:
    print(__doc__)
    sys.exit(code)


def _require_username(args) -> str:
    if len(args) < 3:
        _usage_and_exit()
    return args[2].strip()


def cmd_create_admin(username: str) -> None:
    if not username or any(c.isspace() for c in username):
        print("Username inválido (não pode estar vazio nem conter espaços).")
        sys.exit(1)
    if User.query.filter_by(username=username).first():
        print(f"O utilizador '{username}' já existe. Use 'reset-password' para alterar a password.")
        sys.exit(1)
    password = _read_new_password()
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"\n[OK] Administrador '{username}' criado com sucesso.")


def cmd_reset_password(username: str) -> None:
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"Utilizador '{username}' não encontrado.")
        sys.exit(1)
    password = _read_new_password()
    user.set_password(password)
    db.session.commit()
    print(f"\n[OK] Password de '{username}' actualizada.")


def cmd_delete_admin(username: str) -> None:
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"Utilizador '{username}' não encontrado.")
        sys.exit(1)
    confirm = input(f"Eliminar utilizador '{username}'? Escreva 'sim' para confirmar: ").strip().lower()
    if confirm != "sim":
        print("Cancelado.")
        sys.exit(0)
    db.session.delete(user)
    db.session.commit()
    print(f"[OK] Utilizador '{username}' eliminado.")


def cmd_list_admins() -> None:
    users = User.query.order_by(User.username).all()
    if not users:
        print("(nenhum administrador registado)")
        return
    for u in users:
        print(f"- id={u.id}  username={u.username}")


def main() -> None:
    if len(sys.argv) < 2:
        _usage_and_exit()

    cmd = sys.argv[1]
    app = create_app()
    with app.app_context():
        if cmd == "create-admin":
            cmd_create_admin(_require_username(sys.argv))
        elif cmd == "reset-password":
            cmd_reset_password(_require_username(sys.argv))
        elif cmd == "delete-admin":
            cmd_delete_admin(_require_username(sys.argv))
        elif cmd == "list-admins":
            cmd_list_admins()
        else:
            _usage_and_exit()


if __name__ == "__main__":
    main()
