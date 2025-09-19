from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.dashboard import bp
from app.models import AttendanceRecord, User, LeaveRequest
from app import db
from datetime import date, datetime, time
from sqlalchemy import func

@bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    attendance_record = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == current_user.id,
        func.date(AttendanceRecord.check_in_time) == today
    ).first()

    return render_template('dashboard/dashboard.html', title='Dashboard', record=attendance_record)

@bp.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    today = date.today()
    
    attendance_record = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == current_user.id,
        func.date(AttendanceRecord.check_in_time) == today
    ).first()

    if attendance_record is None:
        # Check-in
        check_in_time = datetime.utcnow()
        
        # Define the official check-in time (8:05 AM)
        official_check_in_time = time(8, 5)

        # Determine the status
        if check_in_time.time() <= official_check_in_time:
            status = 'A Tiempo'
        else:
            status = 'Tarde'

        new_record = AttendanceRecord(
            employee=current_user, 
            check_in_time=check_in_time,
            status=status
        )
        db.session.add(new_record)
        flash('¡Entrada marcada con éxito!', 'success')
    elif attendance_record.check_out_time is None:
        # Check-out
        attendance_record.check_out_time = datetime.utcnow()
        flash('¡Salida marcada con éxito!', 'success')
    else:
        # Already checked out
        flash('Ya has completado tu jornada por hoy.', 'info')

    db.session.commit()
    return redirect(url_for('dashboard.dashboard'))

@bp.route('/mark_lunch', methods=['POST'])
@login_required
def mark_lunch():
    today = date.today()
    
    attendance_record = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == current_user.id,
        func.date(AttendanceRecord.check_in_time) == today
    ).first()

    if not attendance_record:
        flash('Debes marcar tu entrada antes de iniciar el almuerzo.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    if attendance_record.lunch_start_time is None:
        # Start lunch
        attendance_record.lunch_start_time = datetime.utcnow()
        flash('¡Inicio de almuerzo marcado con éxito!', 'success')
    elif attendance_record.lunch_end_time is None:
        # End lunch
        attendance_record.lunch_end_time = datetime.utcnow()
        flash('¡Fin de almuerzo marcado con éxito!', 'success')
    else:
        flash('Ya has completado tu almuerzo por hoy.', 'info')

    db.session.commit()
    return redirect(url_for('dashboard.dashboard'))

@bp.route('/leave', methods=['GET', 'POST'])
@login_required
def leave():
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        leave_type = request.form.get('leave_type')

        if not start_date_str or not end_date_str or not leave_type:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('dashboard.leave'))

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if end_date < start_date:
            flash('La fecha de fin no puede ser anterior a la fecha de inicio.', 'danger')
            return redirect(url_for('dashboard.leave'))

        new_request = LeaveRequest(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            status='Pendiente'
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Solicitud de ausencia enviada con éxito.', 'success')
        return redirect(url_for('dashboard.leave'))

    leave_requests = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.request_date.desc()).all()
    return render_template('dashboard/leave.html', title='Gestionar Ausencias', requests=leave_requests)
