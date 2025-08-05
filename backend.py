from flask import Flask, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    # Buraya chatbot cevabı eklenir
    bot_reply = f"Bu '{user_message}' için en yüksek fiyatli ülke Norveç (örnek cevap)"

    return jsonify({"response": bot_reply})

if __name__ == "__main__":
    app.run(port=5000, debug=True)

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)
model = genai.GenerativeModel("models/gemini-2.5-pro")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")

    if message.strip() == "":
        return jsonify({"response": "Mesaj boş."})

    response = model.generate_content(message)

    return jsonify({"response": response.text})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
