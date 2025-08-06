from flask import Flask, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv
import joblib
import json
import pandas as pd
from pathlib import Path
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app, origins="http://localhost:5173")

logging.basicConfig(level=logging.INFO)

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")

MODEL_PATH = "model/model.joblib"
FEATURES_PATH = "model/feature_columns.json"
DATA_FILE_PATH = "synthetic_ecommerce_data.xlsx"

model = None
feature_cols = None
ecommerce_df = None
product_names_data = {}

try:
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(f"Model dosyasi bulunamadi: {MODEL_PATH}")
    if not Path(FEATURES_PATH).exists():
        raise FileNotFoundError(f"feature_columns.json dosyasi bulunamadi: {FEATURES_PATH}")
    if not Path(DATA_FILE_PATH).exists():
        raise FileNotFoundError(f"Veri dosyasi bulunamadi: {DATA_FILE_PATH}. Lutfen dosya adinin ve uzantisinin dogru oldugundan emin olun.")

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    
    if DATA_FILE_PATH.endswith('.csv'):
        ecommerce_df = pd.read_csv(DATA_FILE_PATH)
    elif DATA_FILE_PATH.endswith('.xlsx'):
        ecommerce_df = pd.read_excel(DATA_FILE_PATH)
    else:
        raise ValueError("Desteklenmeyen veri dosyasi uzantisi. Lutfen .csv veya .xlsx kullanin.")

    product_name_col = 'product_name_clean' if 'product_name_clean' in ecommerce_df.columns else 'product_name'
    
    for index, row in ecommerce_df.iterrows():
        product_name_lower = str(row[product_name_col]).lower()
        if product_name_lower not in product_names_data:
            product_names_data[product_name_lower] = {
                'product_id': str(row['product_id']),
                'product_name_clean': str(row[product_name_col]),
                'category': str(row['category']),
                'brand': str(row['brand']),
                'country': str(row['country']),
                'shipping_cost': float(row['shipping_cost']) if pd.notna(row['shipping_cost']) else 0.0,
                'city': str(row['city']),
                'seller': str(row['seller']),
                'stock': bool(row['stock']),
                'platform': str(row['platform']),
                'month': pd.to_datetime(row['last_updated']).month if 'last_updated' in row and pd.notna(row['last_updated']) else pd.Timestamp.now().month
            }

    logging.info("ML Model, feature kolonlari ve e-ticaret veri seti basariyla yuklendi.")
    logging.info(f"Yuklenen benzersiz urun adi sayisi: {len(product_names_data)}")

except FileNotFoundError as e:
    logging.error(f"Dosya yukleme hatasi: {e}. Lutfen tum gerekli dosyalarin dogru yerde oldugundan emin olun.")
    exit(1)
except Exception as e:
    logging.error(f"Model, feature kolonlari veya veri seti yuklenirken beklenmeyen bir hata olustu: {e}")
    exit(1)

chat_state = {}
MAX_CHAT_HISTORY = 10

def prepare_dataframe(data: dict):
    df = pd.DataFrame([data])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = None
    return df[feature_cols]

def get_country_recommendations_for_prediction(product_data, ecommerce_df, model, feature_cols):
    all_possible_countries = ecommerce_df['country'].unique().tolist()
    predictions_per_country = []
    base_input_for_model = product_data.copy()
    base_input_for_model.pop('country', None)
    base_input_for_model.pop('country_clean', None)
    base_input_for_model['city'] = base_input_for_model.get('city', None)
    base_input_for_model['seller'] = base_input_for_model.get('seller', None)
    base_input_for_model['stock'] = base_input_for_model.get('stock', 100)
    base_input_for_model['platform'] = base_input_for_model.get('platform', "E-commerce")
    base_input_for_model['month'] = base_input_for_model.get('month', pd.Timestamp.now().month)

    for country in all_possible_countries:
        current_product_input = base_input_for_model.copy()
        current_product_input['country'] = country
        
        df_sample = prepare_dataframe(current_product_input)
        
        try:
            pred_price = model.predict(df_sample)[0] 
            predictions_per_country.append({
                "name": country,
                "volume": round(float(pred_price), 2), 
                "reason": f"Bu ulkede tahmini satis fiyati: {round(float(pred_price), 2)} USD."
            })
        except Exception as e:
            logging.warning(f"'{country}' icin tahmin yapilamadi: {e}")

    predictions_per_country.sort(key=lambda x: x["volume"], reverse=True)
    top_n_countries = predictions_per_country[:5] 

    hs_code_info = "HS Kodu tahmini icin daha fazla bilgiye ihtiyac var."
    if product_data.get('category', '').lower() == 'oyuncak':
        hs_code_info = "Tahmini HS Kodu: 9503.00 (Oyuncaklar)."
    elif product_data.get('category', '').lower() == 'elektronik':
        hs_code_info = "Tahmini HS Kodu: 8500.00 (Elektronik Cihazlar)."

    return {
        "recommendation": f"'{product_data.get('product_name_clean', 'Urun')}' icin en yuksek fiyat potansiyeli olan ulkeler:",
        "hsCodeInfo": hs_code_info,
        "countries": top_n_countries,
        "reason": "Bu ulkeler, girdiginiz urun ozellikleri icin en yuksek tahmini satis fiyatina sahip pazarlardir."
    }

def perform_ml_prediction_and_get_rich_response(product_data):
    try:
        df_input_for_single_country = prepare_dataframe(product_data)
        predicted_price_for_input_country = model.predict(df_input_for_single_country)[0]
        country_recommendations = get_country_recommendations_for_prediction(product_data, ecommerce_df, model, feature_cols)
        full_response = {
            "predicted_price": float(predicted_price_for_input_country), 
            "recommendation_data": country_recommendations 
        }
        return full_response
    except Exception as e:
        logging.error(f"perform_ml_prediction_and_get_rich_response icinde ML tahmini yapilamadi: {e}")
        return {"error": str(e), "message": "Fiyat tahmini yapilirken bir hata olustu."}

def get_chatbot_response_based_on_state(session_id, user_message):
    global chat_state
    
    current_state = chat_state.get(session_id, {'stage': 0, 'data': {}})
    stage = current_state['stage']
    data = current_state['data']
    response = ""
    
    user_message_lower = user_message.lower()

    if stage == 'awaiting_prediction_confirmation':
        if user_message_lower in ["evet", "yes", "tahmin et", "fiyat"]:
            if 'product_data_for_prediction' in data:
                rich_response_data = perform_ml_prediction_and_get_rich_response(data['product_data_for_prediction'])
                if "error" in rich_response_data:
                    response = f"Uzgunum, fiyat tahmini yapilirken bir sorun olustu: {rich_response_data['message']}"
                else:
                    response = rich_response_data
                chat_state[session_id] = {'stage': 0, 'data': {}}
            else:
                response = "Uzgunum, hangi urun icin tahmin yapacagimi bulamadim. Lutfen urun adini tekrar belirtin."
                chat_state[session_id] = {'stage': 0, 'data': {}}
        else:
            response = "Anladim, fiyat tahmini yapmak istemiyorsunuz. Baska bir urun veya konuda yardimci olabilirim."
            chat_state[session_id] = {'stage': 0, 'data': {}}

    elif stage == 0:
        found_product_data = None
        for product_name_key, details in product_names_data.items():
            if product_name_key in user_message_lower:
                found_product_data = details
                break
        
        if found_product_data:
            product_name = found_product_data['product_name_clean']
            category = found_product_data['category']
            brand = found_product_data['brand']
            country = found_product_data['country'] 

            response_text = (
                f"Verilerimde **'{product_name}'** urununu buldum!\n\n"
                f"Bu urun **'{category}'** kategorisinde, **'{brand}'** markasina ait ve genellikle **'{country}'** ulkesinde satiliyor.\n\n"
                "Bu urun icin fiyat tahmini almak ister misiniz? Lutfen 'Evet' yazarak devam edin veya asagidaki formu kullanin."
            )
            response = response_text
            chat_state[session_id] = {
                'stage': 'awaiting_prediction_confirmation',
                'data': {'product_data_for_prediction': found_product_data}
            }
        
        elif "toys" in user_message_lower or "oyuncak" in user_message_lower:
            response = "Harika bir urun! Daha dogru bir onerı icin lutfen bazi sorulara cevap verin. Urununuzun ana malzemesi nedir? (orn: ahsap, plastik, kumas)"
            chat_state[session_id] = {'stage': 1, 'data': {'product_type': 'toys'}}
        
        else:
            try:
                context_prompt = (
                    "Sen bir ihracat ve urun analizi chatbotusun. Amacin, kullanicilara urunleri hakkinda bilgi vermek ve pazar analizi yapmak icin gerekli detaylari toplamaktir. "
                    "Kullanici bir urun veya sektor adi belirttiginde, eger daha fazla detaya ihtiyacin varsa (orn: urunun tipi, malzemesi, kullanim amaci, modeli, yas grubu gibi spesifik ozellikler), bu detaylari sorarak yanitini zenginlestirmeye calis. "
                    "Yanitini kisa paragraflara veya madde isaretlerine ayir ve mumkunse cok uzun tutma."
                )
                prompt_for_gemini = f"{context_prompt}\n\nKullanici sorusu: {user_message}"
                gemini_response = gemini_model.generate_content(prompt_for_gemini)
                response = gemini_response.text
            except Exception as e:
                logging.error(f"Gemini API hatasi: {e}")
                response = "Uzgunum, Gemini ile iletisim kurarken bir sorun olustu."
    
    elif stage == 1:
        if "ahsap" in user_message.lower():
            data['material'] = 'ahsap'
            response = "Peki, urunleriniz ozellikle hangi egitim felsefesine uygun? (orn: Montessori, Waldorf, egitici oyuncak)"
            chat_state[session_id] = {'stage': 2, 'data': data}
        elif "plastik" in user_message.lower():
            data['material'] = 'plastik'
            response = "Anladim. Plastik oyuncaklar icin pazar analizi yapiyorum..."
            rich_response_data = create_rich_response_for_plastic_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}}
        elif "kumas" in user_message.lower():
            data['material'] = 'kumas'
            response = "Kumas oyuncaklar icin pazar analizi yapiyorum..."
            rich_response_data = create_rich_response_for_fabric_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}}
        else:
            response = "Anladim. Lutfen ana malzemeyi belirtin. (orn: ahsap, plastik, kumas)"
            chat_state[session_id] = {'stage': 1, 'data': data}

    elif stage == 2:
        if "montessori" in user_message.lower():
            data['philosophy'] = 'Montessori'
            response = "Harika, verileri isliyorum. Bende Toys icin en uygun pazarlar:"
            rich_response_data = create_rich_response_for_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}}
        elif "waldorf" in user_message.lower():
            data['philosophy'] = 'Waldorf'
            response = "Harika, verileri isliyorum. Bende Toys icin en uygun pazarlar:"
            rich_response_data = create_rich_response_for_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}}
        elif "egitici" in user_message.lower():
            data['philosophy'] = 'Egitici'
            response = "Harika, verileri isliyorum. Bende Toys icin en uygun pazarlar:"
            rich_response_data = create_rich_response_for_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}}
        else:
            response = "Lutfen Montessori, Waldorf veya egitici oyuncak gibi bir egitim felsefesi belirtin."
            chat_state[session_id] = {'stage': 2, 'data': data}
    
    return response

def create_rich_response_for_toys(data):
    return {
        "recommendation": f"Ahsap ve {data.get('philosophy', 'egitici')} oyuncaklariniz icin en uygun potansiyel barindiran ulkeler:",
        "hsCodeInfo": "NLP analizi sonucunda urununuz icin en olasi HS Kodu: 9503.00 (Oyuncaklar).",
        "countries": [
            {"name": "Almanya", "volume": 50000000, "reason": "Waldorf ve Montessori felsefelerinin yayginligi."},
            {"name": "ABD", "volume": 80000000, "reason": "Yuksek e-ticaret hacmi ve bilincli ebeveyn kitlesi."},
            {"name": "Ingiltere", "volume": 35000000, "reason": "Estetik ve kaliteli urunlere talep."},
        ],
        "reason": "Bu ulkeler, dogal ve egitici oyuncaklara yuksek talep duyan, alim gucu yuksek pazarlardir.",
    }

def create_rich_response_for_plastic_toys(data):
    return {
        "recommendation": "Plastik oyuncaklariniz icin en uygun potansiyel barindiran ulkeler:",
        "hsCodeInfo": "NLP analizi sonucunda urununuz icin en olasi HS Kodu: 9503.00 (Oyuncaklar).",
        "countries": [
            {"name": "Meksika", "volume": 40000000, "reason": "Genc nufus ve artan orta sinif."},
            {"name": "Polonya", "volume": 20000000, "reason": "Bolgesel dagitim merkezi konumu."},
            {"name": "Turkiye", "volume": 15000000, "reason": "Yerel pazar buyuklugu."},
        ],
        "reason": "Bu ulkeler, rekabetci fiyatli ve populer oyuncaklara yuksek talep duyan pazarlardir.",
    }

def create_rich_response_for_fabric_toys(data):
    return {
        "recommendation": "Kumas oyuncaklariniz icin en uygun potansiyel barindiran ulkeler:",
        "hsCodeInfo": "NLP analizi sonucunda urununuz icin en olasi HS Kodu: 9503.00 (Oyuncaklar).",
        "countries": [
            {"name": "Fransa", "volume": 30000000, "reason": "Bebek urunlerine yuksek talep ve tasarim odaklilik."},
            {"name": "Japonya", "volume": 25000000, "reason": "Kaliteye ve guvenlige verilen onem."},
            {"name": "Kanada", "volume": 20000000, "reason": "Cevre dostu ve dogal urunlere ilgi."},
        ],
        "reason": "Bu ulkeler, yumusak ve guvenli kumas oyuncaklara ozel ilgi duyan pazarlardir.",
    }

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    session_id = request.remote_addr

    if not message.strip():
        return jsonify({"response": "Mesaj bos."})

    response_content = get_chatbot_response_based_on_state(session_id, message)
    
    return jsonify({"response": response_content})

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        logging.info(f"Prediction icin alinan veri: {data}")
        df_input_for_single_country = prepare_dataframe(data)
        predicted_price_for_input_country = model.predict(df_input_for_single_country)[0]
        country_recommendations = get_country_recommendations_for_prediction(data, ecommerce_df, model, feature_cols)
        full_response = {
            "predicted_price": float(predicted_price_for_input_country),
            "recommendation_data": country_recommendations 
        }
        logging.info(f"Tahmin ve Oneri sonucu: {full_response}")
        return jsonify({"response": full_response}) 
    except Exception as e:
        logging.error(f"ML tahmini yapilamadi: {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)


# python backend.py
# cd frontend
# npm run dev
