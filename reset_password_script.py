from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    user = User.query.filter_by(username='testuser').first()
    if user:
        user.set_password('testing123')
        db.session.commit()
        print("Contraseña para 'testuser' actualizada exitosamente.")
    else:
        print("Usuario 'testuser' no encontrado.")
