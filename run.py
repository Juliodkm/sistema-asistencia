from app import create_app, db
from flask_migrate import upgrade

app = create_app()

@app.route('/super-secret-migrate')
def super_secret_migrate():
    print("Iniciando migración de la base de datos desde la ruta secreta...")
    try:
        upgrade()
        print("Migración de la base de datos completada con éxito.")
        return "¡Migración completada con éxito!", 200
    except Exception as e:
        print(f"Error durante la migración: {e}")
        return f"Error durante la migración: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
