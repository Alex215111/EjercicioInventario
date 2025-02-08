from flask import Flask, render_template, request, jsonify
import os
import psycopg2
from twilio.rest import Client  

app = Flask(__name__)

# Obtener la URL de la base de datos desde las variables de entorno en Render
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS planchas (
                                id SERIAL PRIMARY KEY,
                                tipo TEXT NOT NULL,
                                cantidad INTEGER NOT NULL,
                                codigo INTEGER UNIQUE NOT NULL,
                                tamanio TEXT NOT NULL
                            )''')
            conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agregar', methods=['POST'])
def agregar_plancha():
    try:
        data = request.json
        tipo = data['tipo']
        cantidad = int(data['cantidad'])
        codigo = int(data['codigo'])
        tamanio = data['tamanio']

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO planchas (tipo, cantidad, codigo, tamanio) VALUES (%s, %s, %s, %s)',
                               (tipo, cantidad, codigo, tamanio))
                conn.commit()
        return jsonify({"message": "Plancha agregada correctamente."}), 200
    except psycopg2.IntegrityError:
        return jsonify({"error": "El código ya existe."}), 400
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

@app.route('/actualizar', methods=['POST'])
def actualizar_stock():
    try:
        data = request.json
        codigo = int(data['codigo'])
        cantidad = int(data['cantidad'])

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('UPDATE planchas SET cantidad = cantidad + %s WHERE codigo = %s', (cantidad, codigo))
                if cursor.rowcount == 0:
                    return jsonify({"error": "Código no encontrado."}), 404
                conn.commit()
        return jsonify({"message": "Stock actualizado correctamente."}), 200
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

@app.route('/quitar', methods=['POST'])
def quitar_stock():
    try:
        data = request.json
        codigo = int(data['codigo'])
        cantidad = int(data['cantidad'])

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT cantidad FROM planchas WHERE codigo = %s', (codigo,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"error": "Código no encontrado."}), 404

                stock_actual = row[0]
                if cantidad > stock_actual:
                    return jsonify({"error": "No puede quitar más planchas de las que hay en stock."}), 400

                nuevo_stock = stock_actual - cantidad
                cursor.execute('UPDATE planchas SET cantidad = %s WHERE codigo = %s', (nuevo_stock, codigo))
                conn.commit()

                # 🚨 Si el stock llega a 0, enviamos una alerta 🚨
                if nuevo_stock <= 1:
                    mensaje = f"El producto con código {codigo} se ha agotado."
                    enviar_alerta_whatsapp(mensaje)

        return jsonify({"message": "Stock reducido correctamente."}), 200
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

    
def enviar_alerta_whatsapp(mensaje):
    """ Envía una alerta de stock por WhatsApp usando Twilio. """
    try:
        import os
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)

        mensaje_whatsapp = client.messages.create(
            body=f"⚠️ Alerta de Stock Agotado\n\n{mensaje}",
            from_="whatsapp:+14155238886",  # Número de Twilio (sandbox)
            to="whatsapp:+56968356479"  # Tu número de WhatsApp
        )
        print(f"✅ Mensaje enviado a WhatsApp: {mensaje_whatsapp.sid}")
    except Exception as e:
        print(f"❌ Error al enviar mensaje de WhatsApp: {e}")


@app.route('/editar', methods=['POST'])
def editar_plancha():
    try:
        data = request.json
        codigo = int(data['codigo'])
        nuevo_tipo = data.get('tipo', None)
        nuevo_tamanio = data.get('tamanio', None)

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM planchas WHERE codigo = %s', (codigo,))
                if not cursor.fetchone():
                    return jsonify({"error": "Código no encontrado."}), 404

                if nuevo_tipo:
                    cursor.execute('UPDATE planchas SET tipo = %s WHERE codigo = %s', (nuevo_tipo, codigo))
                if nuevo_tamanio:
                    cursor.execute('UPDATE planchas SET tamanio = %s WHERE codigo = %s', (nuevo_tamanio, codigo))

                conn.commit()
        return jsonify({"message": "Datos de la plancha actualizados correctamente."}), 200
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

@app.route('/inventario', methods=['GET'])
def mostrar_inventario():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT tipo, cantidad, codigo, tamanio FROM planchas')
            planchas = [
                {
                    "tipo": row[0],
                    "cantidad": row[1],
                    "codigo": row[2],
                    "tamanio": row[3]
                } for row in cursor.fetchall()
            ]
    return jsonify(planchas)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)
