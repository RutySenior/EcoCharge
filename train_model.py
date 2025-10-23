# train_model.py
import mysql.connector
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
import pickle

# ------------------ Connessione al DB ------------------
db = mysql.connector.connect(
    host="mysql-221cedb1-iisgalvanimi-9701.j.aivencloud.com",
    port=17424,
    user="avnadmin",
    password="AVNS_v5ZY1LueloCJza2Bkdd",
    database="EcoCharge"
)
cursor = db.cursor(dictionary=True)

# ------------------ Prelievo dati ------------------
cursor.execute("""
SELECT c.id_colonnina, c.quartiere, c.potenza_kw,
       COUNT(r.id_ricarica) as numero_ricariche,
       COALESCE(SUM(r.energia_erogata_kwh),0) as energia_totale_kwh
FROM colonnine c
LEFT JOIN ricariche r ON c.id_colonnina = r.id_colonnina
GROUP BY c.id_colonnina
""")
data = cursor.fetchall()
df = pd.DataFrame(data)

if df.empty:
    raise ValueError("Il dataset è vuoto. Assicurati di avere dati nel DB.")

# ------------------ Creazione target ------------------
df['uso'] = pd.cut(df['numero_ricariche'], bins=[-1,5,15,1000], labels=['Basso','Medio','Alto'])

# ------------------ Features e target ------------------
X = df[['potenza_kw','numero_ricariche','energia_totale_kwh']]
y = df['uso']

# Encode target
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

# ------------------ Modelli ------------------
# Random Forest
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)
acc_rf = accuracy_score(y_test, y_pred_rf)

# Decision Tree
dt = DecisionTreeClassifier(random_state=42)
dt.fit(X_train, y_train)
y_pred_dt = dt.predict(X_test)
acc_dt = accuracy_score(y_test, y_pred_dt)

# KNN solo se ci sono abbastanza campioni
if len(X_train) >= 1:
    n_neighbors = min(5, len(X_train))
    knn = KNeighborsClassifier(n_neighbors=n_neighbors)
    knn.fit(X_train, y_train)
    y_pred_knn = knn.predict(X_test)
    acc_knn = accuracy_score(y_test, y_pred_knn)
    print(f"Accuracy KNN (n_neighbors={n_neighbors}): {acc_knn:.2f}")
else:
    acc_knn = -1  # per escluderlo dalla scelta del migliore

print(f"Accuracy Random Forest: {acc_rf:.2f}")
print(f"Accuracy Decision Tree: {acc_dt:.2f}")

# ------------------ Selezione del miglior modello ------------------
accuracies = {'RandomForest': acc_rf, 'DecisionTree': acc_dt}
if acc_knn != -1:
    accuracies['KNN'] = acc_knn

best_model_name = max(accuracies, key=accuracies.get)
print("Miglior modello:", best_model_name)

if best_model_name == 'RandomForest':
    best_model = rf
elif best_model_name == 'DecisionTree':
    best_model = dt
else:
    best_model = knn

# ------------------ Salvataggio modello ------------------
with open('model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

print("Modello salvato in model.pkl")