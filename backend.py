from flask import Flask, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv
import joblib
from flask_cors import CORS



load_dotenv()

app = Flask(__name__)
CORS(app)


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("models/gemini-2.5-pro")

ml_model_path = os.path.join("model", "ecomm_price_model.joblib")
ml_model = None
if os.path.exists(ml_model_path):
    try:
        ml_model = joblib.load(ml_model_path)
        print("✅ ML modeli yüklendi.")
    except:
        print("⚠️ ML modeli yüklenemedi.")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"response": "Mesaj boş gönderilemez."})

    try:
        gemini_response = gemini_model.generate_content(user_message)
        bot_reply = gemini_response.text
    except Exception as e:
        bot_reply = f"Gemini cevabi alinamadi: {str(e)}"

    ml_reply = ""
    if ml_model:
        try:

            prediction = ml_model.predict([[len(user_message)]])
            ml_reply = f"\nTahmini fiyat: {prediction[0]} $"
        except Exception as e:
            ml_reply = f"\n(Tahmin yapilamadi: {str(e)})"

    return jsonify({"response": bot_reply + ml_reply})

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# asya