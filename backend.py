from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    product = data.get("product", "").lower()

    # Sahte cevap
    response = {
        "country": "Norveç",
        "price": 950
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)

