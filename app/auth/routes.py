from flask import render_template, redirect, url_for, flash, request, session
from app import db
from app.auth import bp
from app.models import User
from app.auth.email import send_password_reset_email
from flask_login import login_user, logout_user, current_user

# --- Helper Functions ---

# Helpers for register
def _get_registration_data():
    """Extracts user registration data from the request form."""
    return {
        'username': request.form['username'],
        'email': request.form['email'],
        'password': request.form['password'],
        'first_name': request.form['first_name'],
        'last_name': request.form['last_name'],
        'birth_date': request.form['birth_date'],
        'phone_number': request.form.get('phone_number'),
        'area': request.form['area'],
        'department': request.form['department']
    }

def _validate_new_user(username, email):
    """Checks if username or email already exist in the database."""
    if User.query.filter_by(username=username).first():
        flash('Por favor, utiliza un nombre de usuario diferente.', 'danger')
        return False
    if User.query.filter_by(email=email).first():
        flash('Por favor, utiliza una dirección de correo electrónico diferente.', 'danger')
        return False
    return True

def _create_and_save_user(data):
    """Creates a new user, sets their password, and saves them to the database."""
    user = User(
        username=data['username'], email=data['email'], first_name=data['first_name'],
        last_name=data['last_name'], birth_date=data['birth_date'], phone_number=data['phone_number'],
        area=data['area'], department=data['department']
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return user

# Helpers for login
def _get_login_data():
    """Extracts login credentials from the request form."""
    return request.form['username'], request.form['password']

def _authenticate_user(username, password):
    """Authenticates a user based on username and password."""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    flash('Nombre de usuario o contraseña inválidos', 'danger')
    return None

def _log_in_user(user):
    """Logs in the user and stores their role in the session."""
    login_user(user, remember=True)
    session['role'] = user.role

def _redirect_user_by_role(user):
    """Redirects a user to the appropriate dashboard based on their role."""
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('dashboard.dashboard'))

# Helper for password reset request
def _handle_password_reset_request(email):
    """Finds a user by email and sends a password reset link."""
    user = User.query.filter_by(email=email).first()
    if user:
        send_password_reset_email(user)
    flash('Revisa tu correo para ver las instrucciones de cómo restablecer tu contraseña.', 'info')

# Helpers for password reset
def _verify_password_reset_token(token):
    """Verifies a password reset token and returns the associated user."""
    return User.verify_reset_password_token(token)

def _reset_user_password(user, password):
    """Resets the user's password and saves the change to the database."""
    user.set_password(password)
    db.session.commit()
    flash('Tu contraseña ha sido restablecida.', 'success')


# --- View Functions ---

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        user_data = _get_registration_data()
        if not _validate_new_user(user_data['username'], user_data['email']):
            return redirect(url_for('auth.register'))
        
        _create_and_save_user(user_data)
        flash('¡Felicidades, te has registrado exitosamente!', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Registro')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_user_by_role(current_user)
        
    if request.method == 'POST':
        username, password = _get_login_data()
        user = _authenticate_user(username, password)
        
        if user:
            _log_in_user(user)
            return _redirect_user_by_role(user)
        
        return redirect(url_for('auth.login'))
            
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
        _handle_password_reset_request(email)
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password_request.html', title='Restablecer Contraseña')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
        
    user = _verify_password_reset_token(token)
    if not user:
        flash('El token es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form['password']
        _reset_user_password(user, password)
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', title='Restablecer Contraseña')