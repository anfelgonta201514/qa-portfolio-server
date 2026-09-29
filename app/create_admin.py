import getpass

from app import app
from models import User, db

with app.app_context():
    db.create_all()

    username = input("Usuario admin: ").strip()
    if not username:
        print("El usuario no puede estar vacío.")
        raise SystemExit(1)

    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirmar password: ")
    if password != password_confirm:
        print("Las contraseñas no coinciden.")
        raise SystemExit(1)
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        raise SystemExit(1)

    user = User.query.filter_by(username=username).first()
    if user:
        user.set_password(password)
        db.session.commit()
        print(f"Password actualizado para '{username}'.")
    else:
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Usuario '{username}' creado.")
