import os
from datetime import datetime, timedelta, time
import random
from faker import Faker

# Set up the Flask app context
from app import create_app, db
from app.models import User, AttendanceRecord, LeaveRequest

# Use the app factory with the development configuration
app = create_app(os.getenv('FLASK_CONFIG') or 'development')

fake = Faker('es_ES') # Use Spanish localization

def get_random_time(base_time, min_offset_minutes, max_offset_minutes):
    """Generates a random time within a given offset from a base time."""
    offset = random.randint(min_offset_minutes * 60, max_offset_minutes * 60)
    return base_time + timedelta(seconds=offset)

def seed_database():
    """Seeds the database with an admin user, employees, attendance records, and leave requests."""
    with app.app_context():
        print("Smartly cleaning database...")
        db.session.query(AttendanceRecord).delete()
        db.session.query(LeaveRequest).delete()
        db.session.query(User).filter(User.role != 'admin').delete()
        db.session.commit()

        # --- Ensure Admin User Exists ---
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("Admin user not found. Creating one...")
            admin_user = User(
                username='admin',
                email='admin@empresa.com',
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")

        print("Creating 10 new employee users...")
        users_to_create = []
        departments = ['Tecnología', 'Recursos Humanos', 'Marketing', 'Ventas', 'Finanzas']
        areas = {
            'Tecnología': ['Desarrollo', 'Infraestructura', 'Soporte Técnico'],
            'Recursos Humanos': ['Reclutamiento', 'Nóminas', 'Cultura'],
            'Marketing': ['Digital', 'Contenido', 'Relaciones Públicas'],
            'Ventas': ['Cuentas Clave', 'Ventas Internas'],
            'Finanzas': ['Contabilidad', 'Tesorería']
        }

        for i in range(10):
            profile = fake.profile()
            department = random.choice(departments)
            area = random.choice(areas[department])
            user = User(
                username=profile['username'],
                email=fake.email(), # Use fake.email() for more realistic emails
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role='employee',
                department=department,
                area=area,
                phone_number=fake.phone_number(),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=65)
            )
            user.set_password('password123')
            users_to_create.append(user)
        
        db.session.add_all(users_to_create)
        db.session.commit()

        # --- Seed data for employee users only ---
        employee_users = User.query.filter(User.role == 'employee').all()
        employee_ids = [user.id for user in employee_users]

        print("Creating leave requests for some employees...")
        approved_leaves = []
        for i, user_id in enumerate(employee_ids):
            if i < 2: # Create leave for the first two employees
                start_leave = datetime(2025, 8, 18).date()
                end_leave = datetime(2025, 8, 22).date()
                leave = LeaveRequest(
                    user_id=user_id,
                    start_date=start_leave,
                    end_date=end_leave,
                    leave_type='Vacaciones',
                    status='Aprobado'
                )
                approved_leaves.append(leave)
                db.session.add(leave)
        db.session.commit()

        print("Generating attendance records from 2025-08-01 to 2025-09-12...")
        start_date = datetime(2025, 8, 1).date()
        end_date = datetime(2025, 9, 12).date()
        delta = timedelta(days=1)
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5: # Monday to Friday
                for user in employee_users:
                    on_leave = any(leave.user_id == user.id and leave.start_date <= current_date <= leave.end_date for leave in approved_leaves)
                    
                    if on_leave:
                        record = AttendanceRecord(user_id=user.id, status='Vacaciones', check_in_time=datetime.combine(current_date, time(0,0)))
                    else:
                        check_in_base = datetime.combine(current_date, time(8, 0))
                        check_in = get_random_time(check_in_base, -10, 10) # 7:50 to 8:10
                        status = 'A Tiempo' if check_in.time() <= time(8, 5) else 'Tarde'

                        lunch_start_base = datetime.combine(current_date, time(13, 0))
                        lunch_start = get_random_time(lunch_start_base, -60, 120) # 12:00 to 15:00
                        lunch_duration = timedelta(minutes=random.randint(30, 60))
                        lunch_end = lunch_start + lunch_duration

                        check_out_base = datetime.combine(current_date, time(18, 0))
                        check_out = get_random_time(check_out_base, 0, 20) # 18:00 to 18:20

                        record = AttendanceRecord(
                            user_id=user.id,
                            check_in_time=check_in,
                            check_out_time=check_out,
                            lunch_start_time=lunch_start,
                            lunch_end_time=lunch_end,
                            status=status
                        )
                    db.session.add(record)
            current_date += delta
        db.session.commit()
        print("Database seeding complete!")

if __name__ == '__main__':
    seed_database()