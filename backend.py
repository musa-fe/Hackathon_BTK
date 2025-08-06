from flask import Flask, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv
import joblib
import json
import pandas as pd
from pathlib import Path

# --------------------------
# 1) Uygulama Başlat
# --------------------------
app = Flask(__name__)

# --------------------------
# 2) Gemini Chatbot Ayarı
# --------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("models/gemini-2.5-pro")

# --------------------------
# 3) ML Modelini Yükle
# --------------------------
MODEL_PATH = "model/model.joblib"
FEATURES_PATH = "model/feature_columns.json"

if not Path(MODEL_PATH).exists():
    raise FileNotFoundError("Model dosyasi bulunamadi.")
if not Path(FEATURES_PATH).exists():
    raise FileNotFoundError("feature_columns.json bulunamadi.")

model = joblib.load(MODEL_PATH)
with open(FEATURES_PATH, "r", encoding="utf-8") as f:
    feature_cols = json.load(f)

# --------------------------
# 4) Yardımcı Fonksiyon
# --------------------------
def prepare_dataframe(data: dict):
    """JSON verisini DataFrame'e çevir ve kolonlari hizala"""
    df = pd.DataFrame([data])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = None
    return df[feature_cols]

# --------------------------
# 5) Chatbot API
# --------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    if not message.strip():
        return jsonify({"response": "Mesaj boş."})
    response = gemini_model.generate_content(message)
    return jsonify({"response": response.text})

# --------------------------
# 6) ML Prediction API
# --------------------------
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()  # Örnek: {"category": "Electronics", "price": 100, ...}
        df_input = prepare_dataframe(data)
        prediction = model.predict(df_input)
        return jsonify({"predicted_price": float(prediction[0])})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --------------------------
# 7) Server Başlat
# --------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)