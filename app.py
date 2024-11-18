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
from firebase_admin import (credentials, firestore)


app = Flask(__name__)

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

@app.route('/')
def index():
    session_id = request.args.get('session_id')
    duration = request.args.get('duration', '1')  # Duration in minutes

    if not session_id:
        return "Error: 'session_id' cannot be empty.", 400

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
        <meta http-equiv="refresh" content="60">  <!-- Refresh every 60 seconds -->
    </head>
    <body>
        <img id="qr" src="{{ url_for('generate_qr', session_id=session_id) }}" alt="QR Dinámico">
    </body>
    </html>
    ''', session_id=session_id)

@app.route('/generate_qr')
def generate_qr():
    session_id = request.args.get('session_id')

    if not session_id:
        return "Error: 'session_id' cannot be empty.", 400

    # Generate a random token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # Get current time in Peru
    peru_tz = pytz.timezone('America/Lima')
    now = datetime.now(peru_tz)

    # Calculate expiration time (optional, if you want to use it)
    expiration_time = (now + timedelta(minutes=1)).timestamp()

    # Update the session document in Firestore with the new dynamic QR code
    data = {
        'dynamicQRCode': token,
        'lastUpdated': firestore.SERVER_TIMESTAMP
    }

    # Update the session's dynamicQRCode field
    db.collection('sessions').document(session_id).update(data)

    # Generate the QR code with the token
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)

    # Customize the QR code (optional: color, logo)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Optionally add a logo to the QR code
    logo_path = 'logo.png'  # Ensure that 'logo.png' exists in your project directory
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
        print("Warning: 'logo.png' not found.")

    # Return the image as a response
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
