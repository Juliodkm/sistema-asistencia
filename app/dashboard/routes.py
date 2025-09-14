from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.dashboard import bp
from app.models import AttendanceRecord, User
from app import db
from datetime import date, datetime
from sqlalchemy import func

@bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    attendance_record = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == current_user.id,
        func.date(AttendanceRecord.check_in_time) == today
    ).first()

    status = ""
    if attendance_record is None:
        status = "No ha marcado"
    elif attendance_record.check_out_time is None:
        status = "Entrada Marcada"
    else:
        status = "Salida Marcada"

    return render_template('dashboard/dashboard.html', title='Dashboard', status=status)

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
        new_record = AttendanceRecord(employee=current_user, check_in_time=datetime.utcnow())
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