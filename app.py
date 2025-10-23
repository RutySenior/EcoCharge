from flask import Flask, request, jsonify, render_template
import mysql.connector
from flask_restful import Api, Resource
import secrets
import pickle

app = Flask(__name__)
api = Api(app)
app.secret_key = 'chiave_segreta'
# Carica il modello addestrato
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

# Se hai usato LabelEncoder sul target, puoi anche salvare e ricaricare l'encoder
# Qui assumiamo che 0=Basso,1=Medio,2=Alto
label_map = {0:'Basso', 1:'Medio', 2:'Alto'}

# Connessione MySQL
db = mysql.connector.connect(
    host="mysql-221cedb1-iisgalvanimi-9701.j.aivencloud.com",
    port=17424,
    user="avnadmin",
    password="AVNS_v5ZY1LueloCJza2Bkdd",
    database="EcoCharge"
)
cursor = db.cursor(dictionary=True)

@app.route('/mappa')
def mappa_page():
    return render_template('mappa.html')

tokens = {}

class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # Controllo utenti
        cursor.execute("SELECT * FROM utenti WHERE email=%s AND password_hash=%s", (email, password))
        user = cursor.fetchone()
        if user:
            token = secrets.token_hex(16)
            tokens[token] = {'role': 'utente', 'id': user['id_utente']}
            return jsonify({"success": True, "role": "utente", "user_id": user['id_utente'], "token": token})

        # Controllo admin
        cursor.execute("SELECT * FROM amministratori WHERE email=%s AND password_hash=%s", (email, password))
        admin = cursor.fetchone()
        if admin:
            token = secrets.token_hex(16)
            tokens[token] = {'role': 'admin', 'id': admin['id_admin']}
            return jsonify({"success": True, "role": "admin", "admin_id": admin['id_admin'], "token": token})

        return jsonify({"success": False, "message": "Email o password errate"}), 401

api.add_resource(Login, '/login')

class MappaColonnine(Resource):
    def get(self):
        # Recupera tutte le colonnine dal DB
        cursor.execute("SELECT id_colonnina, indirizzo, latitudine, longitudine, potenza_kw, stato FROM colonnine")
        colonnine = cursor.fetchall()
        # Conversione Decimal → float
        for c in colonnine:
            c['latitudine'] = float(c['latitudine'])
            c['longitudine'] = float(c['longitudine'])
            c['potenza_kw'] = float(c['potenza_kw'])
        return colonnine  # JSON restituito automaticamente

api.add_resource(MappaColonnine, '/api/mappa')

class Utenti(Resource):
    def get(self):
        cursor.execute("SELECT * FROM utenti")
        utenti = cursor.fetchall()
        return jsonify(utenti)

    def post(self):
        data = request.get_json()
        cursor.execute("""
            INSERT INTO utenti (nome, cognome, email, telefono, password_hash)
            VALUES (%s,%s,%s,%s,%s)
        """, (data['nome'], data['cognome'], data['email'], data.get('telefono',''), data['password_hash']))
        db.commit()
        return jsonify({"message":"Utente creato"}), 201

api.add_resource(Utenti, '/utenti')

# ---------------- AUTO ----------------
class Auto(Resource):
    def get(self):
        cursor.execute("SELECT * FROM auto")
        auto = cursor.fetchall()
        return jsonify(auto)

    def post(self):
        data = request.get_json()
        cursor.execute("""
            INSERT INTO auto (id_utente, marca, modello, targa, capacita_batteria_kwh, potenza_massima_kw)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (data['id_utente'], data['marca'], data['modello'], data['targa'], data['capacita_batteria_kwh'], data['potenza_massima_kw']))
        db.commit()
        return jsonify({"message":"Auto creata"}), 201

api.add_resource(Auto, '/auto')

# ---------------- COLONNINE ----------------
class Colonnine(Resource):
    def get(self):
        cursor.execute("SELECT * FROM colonnine")
        colonnine = cursor.fetchall()
        for c in colonnine:
            c['latitudine'] = float(c['latitudine'])
            c['longitudine'] = float(c['longitudine'])
            c['potenza_kw'] = float(c['potenza_kw'])
        return jsonify(colonnine)

    def post(self):
        data = request.get_json()
        cursor.execute("""
            INSERT INTO colonnine (id_admin, indirizzo, quartiere, nil, latitudine, longitudine, potenza_kw, stato)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get('id_admin'),
            data['indirizzo'],
            data.get('quartiere',''),
            data.get('nil',''),
            data['latitudine'],
            data['longitudine'],
            data['potenza_kw'],
            data.get('stato','libera')
        ))
        db.commit()
        return jsonify({"message":"Colonnina creata"}), 201

api.add_resource(Colonnine, '/colonnine')

# ---------------- COLONNINA SINGOLA ----------------
class Colonnina(Resource):
    def get(self, id_colonnina):
        cursor.execute("SELECT * FROM colonnine WHERE id_colonnina=%s", (id_colonnina,))
        col = cursor.fetchone()
        if not col:
            return {"message":"Colonnina non trovata"}, 404
        col['latitudine'] = float(col['latitudine'])
        col['longitudine'] = float(col['longitudine'])
        col['potenza_kw'] = float(col['potenza_kw'])
        return jsonify(col)

    def put(self, id_colonnina):
        data = request.get_json()
        cursor.execute("""
            UPDATE colonnine
            SET indirizzo=%s, quartiere=%s, nil=%s, latitudine=%s, longitudine=%s, potenza_kw=%s, stato=%s
            WHERE id_colonnina=%s
        """, (
            data['indirizzo'], data.get('quartiere',''), data.get('nil',''),
            data['latitudine'], data['longitudine'], data['potenza_kw'], data.get('stato','libera'),
            id_colonnina
        ))
        db.commit()
        return jsonify({"message":"Colonnina aggiornata"})

    def delete(self, id_colonnina):
        cursor.execute("DELETE FROM colonnine WHERE id_colonnina=%s", (id_colonnina,))
        db.commit()
        return jsonify({"message":"Colonnina eliminata"})

api.add_resource(Colonnina, '/colonnine/<int:id_colonnina>')

# ---------------- RICARICHE ----------------
class Ricariche(Resource):
    def get(self):
        cursor.execute("SELECT * FROM ricariche")
        ricariche = cursor.fetchall()
        for r in ricariche:
            r['energia_erogata_kwh'] = float(r['energia_erogata_kwh'])
            r['costo'] = float(r['costo']) if r['costo'] is not None else 0
        return jsonify(ricariche)

    def post(self):
        data = request.get_json()
        cursor.execute("""
            INSERT INTO ricariche (id_colonnina, id_auto, data_inizio, data_fine, energia_erogata_kwh, costo)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (data['id_colonnina'], data.get('id_auto'), data['data_inizio'], data['data_fine'],
              data['energia_erogata_kwh'], data.get('costo',0)))
        db.commit()
        return jsonify({"message":"Ricarica registrata"}), 201

api.add_resource(Ricariche, '/ricariche')

# ---------------- PRENOTAZIONI ----------------
class Prenotazioni(Resource):
    def get(self):
        cursor.execute("SELECT * FROM reservations")
        res = cursor.fetchall()
        return jsonify(res)

    def post(self):
        data = request.get_json()
        cursor.execute("""
            INSERT INTO reservations (id_colonnina, id_utente, start_time, end_time, status)
            VALUES (%s,%s,%s,%s,%s)
        """, (data['id_colonnina'], data['id_utente'], data['start_time'], data['end_time'], data.get('status','booked')))
        db.commit()
        return jsonify({"message":"Prenotazione creata"}), 201

api.add_resource(Prenotazioni, '/prenotazioni')

# ---------------- PREDIZIONI ----------------
class Predizioni(Resource):
    def get(self):
        cursor.execute("SELECT * FROM predizioni")
        pred = cursor.fetchall()
        for p in pred:
            p['richiesta_prevista'] = float(p['richiesta_prevista'])
            p['energia_prevista_kwh'] = float(p['energia_prevista_kwh'])
        return jsonify(pred)

    def post(self):
        data = request.get_json()
        cursor.execute("""
            INSERT INTO predizioni (id_colonnina, data_predizione, richiesta_prevista, energia_prevista_kwh, modello)
            VALUES (%s,%s,%s,%s,%s)
        """, (data['id_colonnina'], data['data_predizione'], data['richiesta_prevista'],
              data['energia_prevista_kwh'], data['modello']))
        db.commit()
        return jsonify({"message":"Predizione inserita"}), 201

api.add_resource(Predizioni, '/predizioni')

class PredizioneColonnina(Resource):
    def post(self):
        """
        Riceve JSON:
        {
            "potenza_kw": 22,
            "numero_ricariche": 10,
            "energia_totale_kwh": 200
        }
        """
        data = request.get_json()

        try:
            X_new = [[
                float(data['potenza_kw']),
                float(data['numero_ricariche']),
                float(data['energia_totale_kwh'])
            ]]

            pred = model.predict(X_new)[0]
            pred_label = label_map[pred]

            return jsonify({
                "predizione": pred_label,
                "input": data
            })

        except KeyError as e:
            return jsonify({"error": f"Campo mancante: {e}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Aggiungi la rotta
api.add_resource(PredizioneColonnina, '/predizione_colonnina')

if __name__ == '__main__':
    app.run(debug=True)