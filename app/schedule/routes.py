from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required
from app import db
from app.models import Schedule
from app.schedule import schedule_bp as bp
from app.admin.routes import admin_required
from datetime import time

# List all schedules
@bp.route('/')
@login_required
@admin_required
def list_schedules():
    schedules = Schedule.query.order_by(Schedule.name).all()
    return render_template('schedule/list.html', schedules=schedules, title='Gestionar Horarios')

# Create a new schedule
@bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_schedule():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            start_time = time.fromisoformat(request.form.get('start_time'))
            end_time = time.fromisoformat(request.form.get('end_time'))
            grace_period = int(request.form.get('grace_period_minutes', 5))

            if not name or not start_time or not end_time:
                flash('Nombre, Hora de Inicio y Hora de Fin son campos obligatorios.', 'danger')
            else:
                new_schedule = Schedule(
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    grace_period_minutes=grace_period
                )
                db.session.add(new_schedule)
                db.session.commit()
                flash(f'Horario "{name}" creado con éxito.', 'success')
                return redirect(url_for('schedule.list_schedules'))
        except Exception as e:
            flash(f'Error al crear el horario: {str(e)}', 'danger')
            
    return render_template('schedule/create.html', title='Crear Nuevo Horario')

# Edit an existing schedule
@bp.route('/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    if request.method == 'POST':
        try:
            schedule.name = request.form.get('name')
            schedule.start_time = time.fromisoformat(request.form.get('start_time'))
            schedule.end_time = time.fromisoformat(request.form.get('end_time'))
            schedule.grace_period_minutes = int(request.form.get('grace_period_minutes', 5))

            if not schedule.name or not schedule.start_time or not schedule.end_time:
                flash('Nombre, Hora de Inicio y Hora de Fin son campos obligatorios.', 'danger')
            else:
                db.session.commit()
                flash(f'Horario "{schedule.name}" actualizado con éxito.', 'success')
                return redirect(url_for('schedule.list_schedules'))
        except Exception as e:
            flash(f'Error al actualizar el horario: {str(e)}', 'danger')

    return render_template('schedule/edit.html', schedule=schedule, title='Editar Horario')

# Delete a schedule
@bp.route('/delete/<int:schedule_id>', methods=['POST'])
@login_required
@admin_required
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    try:
        # Asegurarse que el horario no está en uso
        if schedule.employees:
            flash('No se puede eliminar el horario porque está asignado a uno o más empleados.', 'danger')
            return redirect(url_for('schedule.list_schedules'))
            
        db.session.delete(schedule)
        db.session.commit()
        flash(f'Horario "{schedule.name}" ha sido eliminado.', 'success')
    except Exception as e:
        flash(f'Error al eliminar el horario: {str(e)}', 'danger')
        
    return redirect(url_for('schedule.list_schedules'))
