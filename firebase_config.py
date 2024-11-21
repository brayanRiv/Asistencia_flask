# firebase_config.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore


def initialize_firebase():
    try:
        # Intentar obtener la aplicación por defecto
        firebase_admin.get_app()
        print("Firebase ya está inicializado.")
    except ValueError:
        # Si no está inicializado, proceder a inicializar
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
        print("Firebase ha sido inicializado.")


# Llamamos a la función para asegurar que Firebase está inicializado
initialize_firebase()

# Obtener el cliente de Firestore
db = firestore.client()
