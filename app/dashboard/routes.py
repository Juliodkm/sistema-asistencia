from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.dashboard import bp
from app.models import AttendanceRecord, User
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