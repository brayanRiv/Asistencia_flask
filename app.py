from flask import Flask, send_file, render_template_string, request
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

app = Flask(__name__)

# Determinar la ruta al archivo de credenciales
if os.path.exists('serviceAccountKey.json'):
    # En Render, el archivo estará en el directorio raíz de la aplicación
    cred_path = 'serviceAccountKey.json'
else:
    # Para desarrollo local, especifica la ruta a tu archivo de credenciales
    cred_path = 'serviceAccountKey.json'

# Inicializar Firebase Admin SDK
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def index():
    class_id = request.args.get('class_id', 'default_class')
    duration = request.args.get('duration', '15')

    if not class_id:
        return "Error: 'class_id' no puede estar vacío.", 400

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
        <meta http-equiv="refresh" content="60">
    </head>
    <body>
        <img id="qr" src="{{ url_for('generate_qr', class_id=class_id, duration=duration) }}" alt="QR Dinámico">
    </body>
    </html>
    ''', class_id=class_id, duration=duration)

@app.route('/generate_qr')
def generate_qr():
    class_id = request.args.get('class_id')
    duration = request.args.get('duration', '15')

    if not class_id:
        return "Error: 'class_id' no puede estar vacío.", 400

    try:
        duration = int(duration)
    except ValueError:
        return "Error: 'duration' debe ser un número entero.", 400

    # Generar un token aleatorio
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # Obtener la hora actual en Perú
    peru_tz = pytz.timezone('America/Lima')
    now = datetime.now(peru_tz)

    # Calcular el tiempo de expiración
    expiration_time = (now + timedelta(minutes=duration)).timestamp()

    # Guardar el token en Firestore
    data = {
        'token': token,
        'class_id': class_id,
        'expiration_time': expiration_time
    }

    db.collection('attendance_tokens').document(class_id).set(data)

    # Generar el código QR personalizado
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)

    # Personalizar el QR (color y logo)
    img = qr.make_image(fill_color="darkblue", back_color="white").convert('RGB')

    # Agregar el logo al centro
    logo_path = 'logo.png'  # Asegúrate de que el archivo logo.png existe
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
        print("Advertencia: El archivo logo.png no se encontró.")

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
