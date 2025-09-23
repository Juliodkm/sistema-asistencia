from app import create_app
from flask import render_template

# Le decimos explícitamente que use la configuración de 'development'
app = create_app('development')

@app.route('/')
def index():
    return render_template('home.html')

if __name__ == '__main__':
    app.run()