from flask_mail import Message

def send_email(subject, recipients, body, mail):
    msg = Message(subject, recipients=recipients, body=body)
    mail.send(msg) 