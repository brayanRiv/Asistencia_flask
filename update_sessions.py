# update_sessions.py
from datetime import datetime, timedelta
import pytz
from firebase_config import db  # Importamos db desde firebase_config.py

def update_session_status():
    peru_tz = pytz.timezone('America/Lima')
    now = datetime.now(peru_tz)

    # Obtener todas las sesiones activas
    sessions_ref = db.collection('sessions')
    active_sessions = sessions_ref.where('active', '==', True).stream()

    for session in active_sessions:
        session_data = session.to_dict()
        end_time = session_data.get('endTime')

        if end_time:
            # Convertir end_time de Firestore Timestamp a datetime con zona horaria
            end_time_datetime = end_time.replace(tzinfo=pytz.utc).astimezone(peru_tz)
            if now >= end_time_datetime:
                # Desactivar la sesión
                sessions_ref.document(session.id).update({'active': False})
                print(f"Sesión {session.id} ha sido desactivada.")
            else:
                print(f"Sesión {session.id} aún está activa.")
        else:
            print(f"Sesión {session.id} no tiene endTime definido.")

if __name__ == '__main__':
    update_session_status()
