# app.py
from flask import Flask, send_file, render_template_string, request, json
import qrcode
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import random
import string
from PIL import Image
import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask_apscheduler import APScheduler

class Config:
    SCHEDULER_API_ENABLED = True

app = Flask(__name__)
app.config.from_object(Config())

# Inicializar Firebase Admin SDK
if os.environ.get('GOOGLE_CREDENTIALS_JSON'):
    # En Heroku, cargamos las credenciales desde la variable de entorno
    cred_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    cred_dict = json.loads(cred_json)
    cred = credentials.Certificate(cred_dict)
else:
    # Para desarrollo local, utilizamos el archivo de credenciales
    cred_path = 'serviceAccountKey.json'
    cred = credentials.Certificate(cred_path)

firebase_admin.initialize_app(cred)
db = firestore.client()

scheduler = APScheduler()

def get_active_session(session_id):
    if not session_id:
        return None, ("Error: 'session_id' no puede estar vacío.", 400)

    # Obtener la sesión de Firestore
    session_ref = db.collection('sessions').document(session_id)
    session_doc = session_ref.get()
    if not session_doc.exists:
        return None, ("Error: Sesión no encontrada.", 404)

    session_data = session_doc.to_dict()

    # Verificar si la sesión sigue activa
    peru_tz = pytz.timezone('America/Lima')
    now = datetime.now(peru_tz)
    end_time = session_data.get('endTime')  # Esto es un timestamp de Firestore
    tolerance_minutes = session_data.get('toleranceMinutes', 0)

    if end_time:
        end_time_datetime = end_time.replace(tzinfo=pytz.utc).astimezone(peru_tz)
        total_allowed_time = end_time_datetime + timedelta(minutes=tolerance_minutes * 2)
        if now > total_allowed_time:
            # Desactivar la sesión
            session_ref.update({'active': False})
            return None, ("La sesión ha finalizado.", 200)

    return session_data, None

@scheduler.task('interval', id='update_session_status', minutes=1)
def update_session_status():
    peru_tz = pytz.timezone('America/Lima')
    now = datetime.now(peru_tz)

    # Obtener todas las sesiones activas
    sessions_ref = db.collection('sessions')
    active_sessions = sessions_ref.where('active', '==', True).stream()

    for session in active_sessions:
        session_data = session.to_dict()
        end_time = session_data.get('endTime')
        tolerance_minutes = session_data.get('toleranceMinutes', 0)

        if end_time:
            end_time_datetime = end_time.replace(tzinfo=pytz.utc).astimezone(peru_tz)
            total_allowed_time = end_time_datetime + timedelta(minutes=tolerance_minutes * 2)
            if now > total_allowed_time:
                # Desactivar la sesión
                sessions_ref.document(session.id).update({'active': False})
                print(f"Sesión {session.id} ha sido desactivada.")

@app.route('/')
def index():
    session_id = request.args.get('session_id')
    session_data, error_response = get_active_session(session_id)
    if error_response:
        return error_response  # Esto devuelve (mensaje, código de estado)

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>QR Dinámico</title>
        <style>
            body, html {
                margin: 0;
                padding: 0;
                overflow: hidden;
                width: 100%;
                height: 100%;
                background-color: #ffffff;
            }
            #qr {
                width: 100vw;
                height: 100vh;
                object-fit: contain;
            }
        </style>
        <meta http-equiv="refresh" content="60">  <!-- Refresh cada 60 segundos -->
    </head>
    <body>
        <img id="qr" src="{{ url_for('generate_qr', session_id=session_id) }}" alt="QR Dinámico">
    </body>
    </html>
    ''', session_id=session_id)

@app.route('/generate_qr')
def generate_qr():
    session_id = request.args.get('session_id')
    session_data, error_response = get_active_session(session_id)
    if error_response:
        return error_response  # Esto devuelve (mensaje, código de estado)

    # Generar un token aleatorio
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # Actualizar el campo dynamicQRCode de la sesión en Firestore
    data = {
        'dynamicQRCode': token,
        'lastUpdated': firestore.SERVER_TIMESTAMP
    }

    session_ref = db.collection('sessions').document(session_id)
    session_ref.update(data)

    # Generar el código QR con el token
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)

    # Personalizar el código QR (opcional: color, logo)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Opcionalmente agregar un logo al código QR
    logo_path = 'logo.png'  # Asegúrate de que 'logo.png' existe en tu directorio del proyecto
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        logo_size = (60, 60)
        logo = logo.resize(logo_size)
        pos = (
            (img.size[0] - logo_size[0]) // 2,
            (img.size[1] - logo_size[1]) // 2
        )
        img.paste(logo, pos)
    else:
        print("Advertencia: 'logo.png' no encontrado.")

    # Devolver la imagen como respuesta
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    app.run(debug=True)