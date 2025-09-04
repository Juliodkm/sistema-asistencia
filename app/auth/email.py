from flask import render_template, current_app
from flask_mail import Message
from app import mail

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    msg = Message(
        '[Sistema de Asistencia] Restablecer tu Contraseña',
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user.email]
    )
    msg.html = render_template(
        'email/reset_password.html',
        user=user,
        token=token
    )
    mail.send(msg)
