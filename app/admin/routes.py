from flask import render_template, flash, redirect, url_for, abort, request, send_file, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AttendanceRecord, User, LeaveRequest, Schedule
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

@bp.route('/calendar')
@login_required
@admin_required
def calendar():
    return render_template('admin/calendar.html', title='Calendario de Equipo')

@bp.route('/calendar-events')
@login_required
@admin_required
def calendar_events():
    try:
        approved_requests = db.session.query(LeaveRequest).join(User).filter(LeaveRequest.status == 'Aprobado').all()
        
        events = []
        for req in approved_requests:
            # FullCalendar's end date is exclusive, so add one day to make it inclusive
            end_date = req.end_date + timedelta(days=1)
            events.append({
                'title': f"{req.employee.first_name} {req.employee.last_name}",
                'start': req.start_date.isoformat(),
                'end': end_date.isoformat(),
                'allDay': True
            })
        return jsonify(events)
    except Exception as e:
        # Log the error e
        return jsonify({'error': 'Could not fetch events'}), 500

@bp.route('/leave_requests')
@login_required
@admin_required
def leave_requests():
    pending_requests = db.session.query(LeaveRequest, User).join(User).filter(LeaveRequest.status == 'Pendiente').all()
    return render_template('admin/leave_requests.html', requests=pending_requests, title='Solicitudes de Ausencia')

@bp.route('/process_leave/<int:request_id>', methods=['POST'])
@login_required
@admin_required
def process_leave(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    action = request.form.get('action')

    if action == 'approve':
        leave_request.status = 'Aprobado'
        flash(f'Solicitud de {leave_request.employee.first_name} ha sido aprobada.', 'success')
    elif action == 'reject':
        leave_request.status = 'Rechazado'
        flash(f'Solicitud de {leave_request.employee.first_name} ha sido rechazada.', 'warning')

    db.session.commit()
    return redirect(url_for('admin.leave_requests'))

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
    user = User.query.get_or_404(user_id)
    schedules = Schedule.query.all()

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date() if request.form['birth_date'] else None
        user.phone_number = request.form['phone_number']
        user.area = request.form['area']
        user.department = request.form['department']
        user.role = request.form['role']
        schedule_id = request.form.get('schedule_id')
        user.schedule_id = int(schedule_id) if schedule_id else None

        if request.form['password']:
            user.set_password(request.form['password'])
        
        db.session.commit()
        flash('Usuario actualizado con éxito.', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/edit_user.html', user=user, schedules=schedules, title='Editar Usuario')

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
    summary_stats = {}

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            end_date_dt = datetime.combine(end_date, datetime.max.time()) # for range queries

            # Query for detailed paginated view
            records_query = db.session.query(AttendanceRecord, User).join(
                User, AttendanceRecord.user_id == User.id
            ).filter(
                AttendanceRecord.check_in_time >= start_date,
                AttendanceRecord.check_in_time < end_date_dt
            ).order_by(AttendanceRecord.check_in_time.desc())
            
            pagination = records_query.paginate(page=page, per_page=20, error_out=False)

            # --- Analysis Part ---
            all_records = records_query.all()
            if not all_records:
                flash('No se encontraron registros en el rango de fechas seleccionado.', 'info')
            else:
                # Convert to DataFrame for analysis
                data = [{
                    'user_id': user.id,
                    'username': user.username,
                    'check_in': record.check_in_time,
                    'check_out': record.check_out_time,
                    'lunch_start': record.lunch_start_time,
                    'lunch_end': record.lunch_end_time,
                    'status': record.status
                } for record, user in all_records]
                df = pd.DataFrame(data)

                # Calculate worked hours
                df['work_duration'] = (df['check_out'] - df['check_in']).dt.total_seconds()
                df['lunch_duration'] = (df['lunch_end'] - df['lunch_start']).dt.total_seconds().fillna(0)
                df['worked_hours'] = (df['work_duration'] - df['lunch_duration']) / 3600

                # Group for stats
                summary = df.groupby(['user_id', 'username']).agg(
                    dias_trabajados=('check_in', 'count'),
                    total_tardanzas=('status', lambda x: (x == 'Tarde').sum()),
                    horas_totales=('worked_hours', 'sum')
                ).reset_index()

                # Calculate leave days
                leave_requests = LeaveRequest.query.filter(
                    LeaveRequest.status == 'Aprobado',
                    LeaveRequest.start_date <= end_date,
                    LeaveRequest.end_date >= start_date
                ).all()
                
                leave_summary = {}
                for leave in leave_requests:
                    # Calculate overlap with the selected date range
                    overlap_start = max(leave.start_date, start_date)
                    overlap_end = min(leave.end_date, end_date)
                    if overlap_start <= overlap_end:
                        days_on_leave = (overlap_end - overlap_start).days + 1
                        if leave.user_id not in leave_summary:
                            leave_summary[leave.user_id] = {'Vacaciones': 0, 'Enfermedad': 0, 'Permiso Personal': 0}
                        leave_summary[leave.user_id][leave.leave_type] += days_on_leave

                # Combine summaries
                summary['dias_vacaciones'] = summary['user_id'].map(lambda x: leave_summary.get(x, {}).get('Vacaciones', 0))
                summary['dias_enfermedad'] = summary['user_id'].map(lambda x: leave_summary.get(x, {}).get('Enfermedad', 0))
                
                summary_stats = summary.to_dict('records')

        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'danger')

    return render_template('admin/reports.html', 
                           pagination=pagination, 
                           summary_stats=summary_stats,
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

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    end_date_dt = datetime.combine(end_date, datetime.max.time())

    # Get all records for the date range
    records_query = db.session.query(AttendanceRecord, User).join(
        User, AttendanceRecord.user_id == User.id
    ).filter(
        AttendanceRecord.check_in_time >= start_date,
        AttendanceRecord.check_in_time < end_date_dt
    ).order_by(User.username, AttendanceRecord.check_in_time)
    
    all_records = records_query.all()

    if not all_records:
        flash('No hay datos para exportar en el rango seleccionado.', 'info')
        return redirect(url_for('admin.reports'))

    # --- Analysis Part for Summary ---
    data = [{
        'user_id': user.id,
        'username': user.username,
        'check_in': record.check_in_time,
        'check_out': record.check_out_time,
        'lunch_start': record.lunch_start_time,
        'lunch_end': record.lunch_end_time,
        'status': record.status
    } for record, user in all_records]
    df = pd.DataFrame(data)

    df['work_duration'] = (df['check_out'] - df['check_in']).dt.total_seconds()
    df['lunch_duration'] = (df['lunch_end'] - df['lunch_start']).dt.total_seconds().fillna(0)
    df['worked_hours'] = (df['work_duration'] - df['lunch_duration']) / 3600

    summary = df.groupby(['user_id', 'username']).agg(
        dias_trabajados=('check_in', 'count'),
        total_tardanzas=('status', lambda x: (x == 'Tarde').sum()),
        horas_totales=('worked_hours', 'sum')
    ).reset_index()

    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.status == 'Aprobado',
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).all()
    
    leave_summary = {}
    for leave in leave_requests:
        overlap_start = max(leave.start_date, start_date)
        overlap_end = min(leave.end_date, end_date)
        if overlap_start <= overlap_end:
            days_on_leave = (overlap_end - overlap_start).days + 1
            if leave.user_id not in leave_summary:
                leave_summary[leave.user_id] = {'Vacaciones': 0, 'Enfermedad': 0, 'Permiso Personal': 0}
            leave_summary[leave.user_id][leave.leave_type] += days_on_leave

    summary['dias_vacaciones'] = summary['user_id'].map(lambda x: leave_summary.get(x, {}).get('Vacaciones', 0))
    summary['dias_enfermedad'] = summary['user_id'].map(lambda x: leave_summary.get(x, {}).get('Enfermedad', 0))
    
    summary_stats = summary.to_dict('records')
    # --- End of Analysis Part ---

    rendered_html = render_template(
        'admin/report_pdf.html', 
        records=all_records, 
        summary_stats=summary_stats,
        start_date=start_date_str, 
        end_date=end_date_str,
        generation_date=date.today().strftime('%d-%m-%Y')
    )
    pdf = HTML(string=rendered_html).write_pdf()

    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'reporte_asistencia_{start_date_str}_a_{end_date_str}.pdf'
    )

@bp.route('/reports/charts-data')
@login_required
@admin_required
def charts_data():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        end_date_dt = datetime.combine(end_date, datetime.max.time())

        # --- Tardanzas por Departamento ---
        attendance_records = db.session.query(AttendanceRecord, User).join(
            User, AttendanceRecord.user_id == User.id
        ).filter(
            AttendanceRecord.check_in_time >= start_date,
            AttendanceRecord.check_in_time < end_date_dt,
            AttendanceRecord.status == 'Tarde'
        ).all()

        if not attendance_records:
            tardanzas_por_departamento = {"labels": [], "data": []}
        else:
            df_tardanzas = pd.DataFrame([{
                'department': user.department
            } for record, user in attendance_records])
            
            tardanzas_counts = df_tardanzas['department'].value_counts()
            tardanzas_por_departamento = {
                "labels": tardanzas_counts.index.tolist(),
                "data": tardanzas_counts.values.tolist()
            }

        # --- Distribución de Ausencias ---
        leave_requests = LeaveRequest.query.filter(
            LeaveRequest.status == 'Aprobado',
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()

        if not leave_requests:
            distribucion_ausencias = {"labels": [], "data": []}
        else:
            leave_data = []
            for req in leave_requests:
                # Calculate overlap days
                overlap_start = max(req.start_date, start_date)
                overlap_end = min(req.end_date, end_date)
                if overlap_start <= overlap_end:
                    days = (overlap_end - overlap_start).days + 1
                    for _ in range(days):
                        leave_data.append({'leave_type': req.leave_type})
            
            if not leave_data:
                 distribucion_ausencias = {"labels": [], "data": []}
            else:
                df_leaves = pd.DataFrame(leave_data)
                ausencias_counts = df_leaves['leave_type'].value_counts()
                distribucion_ausencias = {
                    "labels": ausencias_counts.index.tolist(),
                    "data": ausencias_counts.values.tolist()
                }

        return jsonify({
            "tardanzas_por_departamento": tardanzas_por_departamento,
            "distribucion_ausencias": distribucion_ausencias
        })

    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    except Exception as e:
        # Log error e
        return jsonify({"error": "An internal error occurred."}), 500
