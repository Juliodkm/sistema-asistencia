from flask import render_template, flash, redirect, url_for, abort, request, send_file
from flask_login import login_required, current_user
from app import db
from app.models import AttendanceRecord, User
from app.admin import admin_bp as bp
from functools import wraps
from datetime import datetime, timedelta, date
from sqlalchemy import func
import pandas as pd
import io
from weasyprint import HTML

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = date.today()

    # KPIs
    total_employees = User.query.filter(User.role != 'admin').count()
    present_today = AttendanceRecord.query.filter(func.date(AttendanceRecord.check_in_time) == today, AttendanceRecord.status != 'Vacaciones').count()
    on_leave_today = AttendanceRecord.query.filter(func.date(AttendanceRecord.check_in_time) == today, AttendanceRecord.status == 'Vacaciones').count()
    late_today = AttendanceRecord.query.filter(func.date(AttendanceRecord.check_in_time) == today, AttendanceRecord.status == 'Tarde').count()

    # Recent activity
    recent_records = db.session.query(AttendanceRecord, User).join(User, AttendanceRecord.user_id == User.id).order_by(AttendanceRecord.check_in_time.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                           title='Panel de Administrador',
                           total_employees=total_employees,
                           present_today=present_today,
                           on_leave_today=on_leave_today,
                           late_today=late_today,
                           records=recent_records)

# User Management Routes
@bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users, title='Gestionar Usuarios')

@bp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        # ... (código existente de add_user)
        pass
    return render_template('admin/add_user.html', title='Añadir Usuario')

@bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    # ... (código existente de edit_user)
    pass
    user = User.query.get_or_404(user_id)
    return render_template('admin/edit_user.html', user=user, title='Editar Usuario')

@bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    # ... (código existente de delete_user)
    pass

# Reports Module
@bp.route('/reports', methods=['GET', 'POST'])
@login_required
@admin_required
def reports():
    page = request.args.get('page', 1, type=int)
    start_date_str = request.values.get('start_date')
    end_date_str = request.values.get('end_date')
    pagination = None

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

            records_query = db.session.query(AttendanceRecord, User).join(
                User, AttendanceRecord.user_id == User.id
            ).filter(
                AttendanceRecord.check_in_time >= start_date,
                AttendanceRecord.check_in_time < end_date
            ).order_by(AttendanceRecord.check_in_time.desc())
            
            pagination = records_query.paginate(page=page, per_page=50, error_out=False)
            
            if not pagination.items:
                flash('No se encontraron registros en el rango de fechas seleccionado.', 'info')
        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'danger')

    return render_template('admin/reports.html', 
                           pagination=pagination, 
                           title='Reportes de Asistencia', 
                           start_date=start_date_str, 
                           end_date=end_date_str)

@bp.route('/export/excel')
@login_required
@admin_required
def export_excel():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        flash('Fechas de inicio y fin son requeridas para exportar.', 'danger')
        return redirect(url_for('admin.reports'))

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

    records = db.session.query(AttendanceRecord, User).join(
        User, AttendanceRecord.user_id == User.id
    ).filter(
        AttendanceRecord.check_in_time >= start_date,
        AttendanceRecord.check_in_time < end_date
    ).order_by(AttendanceRecord.check_in_time.desc()).all()

    if not records:
        flash('No hay datos para exportar en el rango seleccionado.', 'info')
        return redirect(url_for('admin.reports'))

    data = []
    for record, user in records:
        data.append({
            'Usuario': user.username,
            'Nombre': user.first_name,
            'Apellido': user.last_name,
            'Entrada': record.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if record.check_in_time else '',
            'Inicio Almuerzo': record.lunch_start_time.strftime('%H:%M:%S') if record.lunch_start_time else '',
            'Fin Almuerzo': record.lunch_end_time.strftime('%H:%M:%S') if record.lunch_end_time else '',
            'Salida': record.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if record.check_out_time else '',
            'Estado': record.status
        })
    
    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='Reporte Asistencia')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'reporte_asistencia_{start_date_str}_a_{end_date_str}.xlsx'
    )

@bp.route('/export/pdf')
@login_required
@admin_required
def export_pdf():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        flash('Fechas de inicio y fin son requeridas para exportar.', 'danger')
        return redirect(url_for('admin.reports'))

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

    records = db.session.query(AttendanceRecord, User).join(
        User, AttendanceRecord.user_id == User.id
    ).filter(
        AttendanceRecord.check_in_time >= start_date,
        AttendanceRecord.check_in_time < end_date
    ).order_by(AttendanceRecord.check_in_time.desc()).all()

    if not records:
        flash('No hay datos para exportar en el rango seleccionado.', 'info')
        return redirect(url_for('admin.reports'))

    rendered_html = render_template('admin/report_pdf.html', records=records, start_date=start_date_str, end_date=end_date_str)
    pdf = HTML(string=rendered_html).write_pdf()

    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'reporte_asistencia_{start_date_str}_a_{end_date_str}.pdf'
    )
