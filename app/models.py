from app import db, login
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Date, DateTime
from flask import current_app
from flask_login import UserMixin
import jwt

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='employee', nullable=False)

    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    birth_date = db.Column(Date, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    area = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(50), nullable=True)
    
    attendance_records = db.relationship('AttendanceRecord', backref='employee', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', backref='employee', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        # Note: datetime.timedelta is needed here. Assuming it's imported where used.
        return jwt.encode(
            {'reset_password': self.id, 'exp': datetime.now(timezone.utc) + jwt.timedelta(seconds=expires_in)},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'], 
                algorithms=['HS256']
            )['reset_password']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
        return db.session.get(User, id)

    def __repr__(self):
        return f'<User {self.username}>'

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    check_in_time = db.Column(DateTime, nullable=True)
    check_out_time = db.Column(DateTime, nullable=True)
    lunch_start_time = db.Column(DateTime, nullable=True)
    lunch_end_time = db.Column(DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False) # 'A Tiempo', 'Tarde', 'Ausente', 'Vacaciones'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<AttendanceRecord {self.id} for User {self.user_id}>'

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(Date, nullable=False)
    end_date = db.Column(Date, nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) # Ej: 'Vacaciones', 'Enfermedad'
    status = db.Column(db.String(50), default='Pendiente', nullable=False) # Ej: 'Aprobado', 'Pendiente', 'Rechazado'
    request_date = db.Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LeaveRequest {self.id} from User {self.user_id}>'
