from flask import render_template, redirect, url_for, flash, request
from app import db
from app.auth import bp
from app.models import User
from app.auth.email import send_password_reset_email
from flask_login import login_user, logout_user, current_user

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        birth_date = request.form['birth_date']
        phone_number = request.form.get('phone_number')
        area = request.form['area']
        department = request.form['department']

        if User.query.filter_by(username=username).first() is not None:
            flash('Por favor, utiliza un nombre de usuario diferente.', 'danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first() is not None:
            flash('Por favor, utiliza una dirección de correo electrónico diferente.', 'danger')
            return redirect(url_for('auth.register'))

        user = User(
            username=username, email=email, first_name=first_name, 
            last_name=last_name, birth_date=birth_date, phone_number=phone_number, 
            area=area, department=department
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('¡Felicidades, te has registrado exitosamente!', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Registro')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Nombre de usuario o contraseña inválidos', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=True)
        return redirect(url_for('dashboard.dashboard'))
    return render_template('auth/login.html', title='Iniciar Sesión')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user)
        flash('Revisa tu correo para ver las instrucciones de cómo restablecer tu contraseña.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title='Restablecer Contraseña')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('El token es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form['password']
        user.set_password(password)
        db.session.commit()
        flash('Tu contraseña ha sido restablecida.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', title='Restablecer Contraseña')
