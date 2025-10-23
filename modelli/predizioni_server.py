from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import pickle

# ---------------- Server ----------------
app = Flask(__name__)
api = Api(app)

# ---------------- Caricamento modello ----------------
with open('modelli/model.pkl', 'rb') as f:
    model = pickle.load(f)

# Label mapping (se target era codificato)
label_map = {0:'Basso', 1:'Medio', 2:'Alto'}

# ---------------- Risorsa Predizione ----------------
class PredizioneColonnina(Resource):
    def post(self):
        """
        JSON input:
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

# ---------------- Endpoint ----------------
api.add_resource(PredizioneColonnina, '/predizione_colonnina')

# ---------------- Avvio server ----------------
if __name__ == '__main__':
    app.run(port=5001, debug=True)