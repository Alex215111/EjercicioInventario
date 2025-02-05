from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# Configuración de la base de datos
DATABASE = 'inventario.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS planchas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO planchas (tipo, cantidad, codigo, tamanio) VALUES (?, ?, ?, ?)',
                           (tipo, cantidad, codigo, tamanio))
            conn.commit()
        return jsonify({"message": "Plancha agregada correctamente."}), 200
    except sqlite3.IntegrityError:
        return jsonify({"error": "El código ya existe."}), 400
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

@app.route('/actualizar', methods=['POST'])
def actualizar_stock():
    try:
        data = request.json
        codigo = int(data['codigo'])
        cantidad = int(data['cantidad'])

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE planchas SET cantidad = cantidad + ? WHERE codigo = ?', (cantidad, codigo))
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

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT cantidad FROM planchas WHERE codigo = ?', (codigo,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "Código no encontrado."}), 404

            stock_actual = row[0]
            if cantidad > stock_actual:
                return jsonify({"error": "No puede quitar más planchas de las que hay en stock."}), 400

            cursor.execute('UPDATE planchas SET cantidad = cantidad - ? WHERE codigo = ?', (cantidad, codigo))
            conn.commit()
        return jsonify({"message": "Stock reducido correctamente."}), 200
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

@app.route('/editar', methods=['POST'])
def editar_plancha():
    try:
        data = request.json
        codigo = int(data['codigo'])
        nuevo_tipo = data.get('tipo', None)
        nuevo_tamanio = data.get('tamanio', None)

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM planchas WHERE codigo = ?', (codigo,))
            if not cursor.fetchone():
                return jsonify({"error": "Código no encontrado."}), 404

            if nuevo_tipo:
                cursor.execute('UPDATE planchas SET tipo = ? WHERE codigo = ?', (nuevo_tipo, codigo))
            if nuevo_tamanio:
                cursor.execute('UPDATE planchas SET tamanio = ? WHERE codigo = ?', (nuevo_tamanio, codigo))

            conn.commit()
        return jsonify({"message": "Datos de la plancha actualizados correctamente."}), 200
    except (ValueError, KeyError):
        return jsonify({"error": "Datos inválidos."}), 400

@app.route('/inventario', methods=['GET'])
def mostrar_inventario():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
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
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)

