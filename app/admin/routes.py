from flask import render_template, flash, redirect, url_for, abort, request
from flask_login import login_required, current_user
from app import db
from app.models import AttendanceRecord, User
from app.admin import admin_bp
from functools import wraps
from datetime import datetime

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    attendance_records = db.session.query(AttendanceRecord, User).join(User, AttendanceRecord.user_id == User.id).order_by(AttendanceRecord.check_in_time.desc()).all()
    return render_template('admin/dashboard.html', records=attendance_records)

# User Management Routes
@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users, title='Gestionar Usuarios')

@admin_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        birth_date_str = request.form.get('birth_date')
        phone_number = request.form.get('phone_number')
        area = request.form.get('area')
        department = request.form.get('department')

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return redirect(url_for('admin.add_user'))
        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está en uso.', 'danger')
            return redirect(url_for('admin.add_user'))

        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date() if birth_date_str else None

        new_user = User(
            username=username,
            email=email,
            role=role,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            phone_number=phone_number,
            area=area,
            department=department
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuario añadido correctamente.', 'success')
        return redirect(url_for('admin.list_users'))
    
    return render_template('admin/add_user.html', title='Añadir Usuario')

@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        # Check for uniqueness if username or email has changed
        new_username = request.form.get('username')
        if user.username != new_username and User.query.filter_by(username=new_username).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        new_email = request.form.get('email')
        if user.email != new_email and User.query.filter_by(email=new_email).first():
            flash('El correo electrónico ya está en uso.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        user.username = new_username
        user.email = new_email
        user.role = request.form.get('role')
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.phone_number = request.form.get('phone_number')
        user.area = request.form.get('area')
        user.department = request.form.get('department')
        
        birth_date_str = request.form.get('birth_date')
        if birth_date_str:
            user.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        else:
            user.birth_date = None

        password = request.form.get('password')
        if password:
            user.set_password(password)
            
        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/edit_user.html', user=user, title='Editar Usuario')

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    # Optional: Add a check to prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.list_users'))
        
    db.session.delete(user)
    db.session.commit()
    flash('Usuario eliminado correctamente.', 'success')
    return redirect(url_for('admin.list_users'))
