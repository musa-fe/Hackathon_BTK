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

# --------------------------
# 1) Uygulama Başlat
# --------------------------
app = Flask(__name__)
# Frontend'inizin çalıştığı doğru portu burada belirtiyoruz.
# Eğer frontend 5173'te çalışıyorsa, bu doğru ayardır.
# Eğer farklı bir portta çalışıyorsa, burayı o porta göre güncelleyin.
CORS(app, origins="http://localhost:5173")

# Logging ayarları
logging.basicConfig(level=logging.INFO)

# --------------------------
# 2) Gemini Chatbot Ayarı
# --------------------------
load_dotenv()
# API anahtarınızın .env dosyasında GOOGLE_API_KEY olarak tanımlandığından emin olun
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Sizin orijinal model adınızı koruyoruz
gemini_model = genai.GenerativeModel("models/gemini-2.5-pro") 

# --------------------------
# 3) ML Modelini Yükle
# --------------------------
# Sizin orijinal dosya yolu tanımlamalarını koruyoruz
MODEL_PATH = "model/model.joblib"
FEATURES_PATH = "model/feature_columns.json"

try:
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(f"Model dosyası bulunamadı: {MODEL_PATH}")
    if not Path(FEATURES_PATH).exists():
        raise FileNotFoundError(f"feature_columns.json dosyası bulunamadı: {FEATURES_PATH}")

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, "r", encoding="utf-8") as f:
        feature_cols = json.load(f)

    logging.info("ML Model ve feature kolonları başarıyla yüklendi.")

except FileNotFoundError as e:
    logging.error(f"Dosya yükleme hatası: {e}")
    exit(1)
except Exception as e:
    logging.error(f"Model veya feature kolonları yüklenirken beklenmeyen bir hata oluştu: {e}")
    exit(1)

# --------------------------
# Chatbot state yönetimi
# --------------------------
chat_state = {}  # session_id: {stage: int, data: dict}
MAX_CHAT_HISTORY = 10 # Örnek için bir limit belirledik

# --------------------------
# 4) Yardımcı Fonksiyon
# --------------------------
def prepare_dataframe(data: dict):
    """JSON verisini DataFrame'e çevir ve kolonları hizala"""
    df = pd.DataFrame([data])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = None # Eğer kolonda veri yoksa None atar
    return df[feature_cols]

# --------------------------
# Yeni chatbot mantığı için yardımcı fonksiyon
# --------------------------
def get_chatbot_response_based_on_state(session_id, user_message):
    global chat_state
    
    current_state = chat_state.get(session_id, {'stage': 0, 'data': {}})
    stage = current_state['stage']
    data = current_state['data']
    response = ""
    
    # Adım 0: Giriş veya genel sohbet
    if stage == 0:
        if "toys" in user_message.lower() or "oyuncak" in user_message.lower():
            response = "Harika bir ürün! Daha doğru bir öneri için lütfen birkaç soruya cevap verin. Ürününüzün ana malzemesi nedir? (örn: ahşap, plastik, kumaş)"
            chat_state[session_id] = {'stage': 1, 'data': {'product_type': 'toys'}}
        else:
            # Standart Gemini yanıtı
            try:
                # Gemini'ye uygulamanın bağlamını belirtiyoruz
                context_prompt = (
                    "Sen bir ihracat ve ürün analizi chatbotusun. Amacın, kullanıcılara ürünleri hakkında bilgi vermek, pazar analizi yapmak ve ihracat süreçlerinde yardımcı olmaktır. "
                    "Kendini bu bağlamda tanıt ve genel sorulara da bu rolünle cevap ver. "
                    "Yanıtını kısa paragraflara veya madde işaretlerine ayır ve mümkünse çok uzun tutma."
                )
                prompt_for_gemini = f"{context_prompt}\n\nKullanıcı sorusu: {user_message}"
                gemini_response = gemini_model.generate_content(prompt_for_gemini)
                response = gemini_response.text
            except Exception as e:
                logging.error(f"Gemini API hatası: {e}")
                response = "Üzgünüm, Gemini ile iletişim kurarken bir sorun oluştu."
    
    # Adım 1: Malzeme sorusu
    elif stage == 1:
        if "ahşap" in user_message.lower():
            data['material'] = 'ahşap'
            response = "Peki, ürünleriniz özellikle hangi eğitim felsefesine uygun? (örn: Montessori, Waldorf, eğitici oyuncak)"
            chat_state[session_id] = {'stage': 2, 'data': data}
        elif "plastik" in user_message.lower():
            data['material'] = 'plastik'
            response = "Anladım. Plastik oyuncaklar için pazar analizi yapıyorum..."
            rich_response_data = create_rich_response_for_plastic_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}} # State'i sıfırla
        elif "kumaş" in user_message.lower():
            data['material'] = 'kumaş'
            response = "Kumaş oyuncaklar için pazar analizi yapıyorum..."
            rich_response_data = create_rich_response_for_fabric_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}} # State'i sıfırla
        else:
            response = "Anladım. Lütfen ana malzemeyi belirtin. (örn: ahşap, plastik, kumaş)"
            chat_state[session_id] = {'stage': 1, 'data': data} # Aynı aşamada kal

    # Adım 2: Felsefe sorusu ve son yanıt (ahşap oyuncaklar için)
    elif stage == 2:
        if "montessori" in user_message.lower():
            data['philosophy'] = 'Montessori'
            response = "Harika, verileri işliyorum. Bende Toys için en uygun pazarlar:"
            rich_response_data = create_rich_response_for_toys(data)
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}} # State'i sıfırla
        elif "waldorf" in user_message.lower():
            data['philosophy'] = 'Waldorf'
            response = "Harika, verileri işliyorum. Bende Toys için en uygun pazarlar:"
            rich_response_data = create_rich_response_for_toys(data) # Waldorf için de aynı yanıtı kullanabiliriz
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}} # State'i sıfırla
        elif "eğitici" in user_message.lower():
            data['philosophy'] = 'Eğitici'
            response = "Harika, verileri işliyorum. Bende Toys için en uygun pazarlar:"
            rich_response_data = create_rich_response_for_toys(data) # Eğitici için de aynı yanıtı kullanabiliriz
            response = rich_response_data
            chat_state[session_id] = {'stage': 0, 'data': {}} # State'i sıfırla
        else:
            response = "Lütfen Montessori, Waldorf veya eğitici oyuncak gibi bir eğitim felsefesi belirtin."
            chat_state[session_id] = {'stage': 2, 'data': data} # Aynı aşamada kal
    
    return response

# Zenginleştirilmiş yanıtı oluşturan fonksiyonlar (chatbot için)
def create_rich_response_for_toys(data):
    return {
        "recommendation": f"Ahşap ve {data.get('philosophy', 'eğitici')} oyuncaklarınız için en uygun potansiyel barındıran ülkeler:",
        "hsCodeInfo": "NLP analizi sonucunda ürününüz için en olası HS Kodu: 9503.00 (Oyuncaklar).",
        "countries": [
            {"name": "Almanya", "volume": 50000000, "reason": "Waldorf ve Montessori felsefelerinin yaygınlığı."},
            {"name": "ABD", "volume": 80000000, "reason": "Yüksek e-ticaret hacmi ve bilinçli ebeveyn kitlesi."},
            {"name": "İngiltere", "volume": 35000000, "reason": "Estetik ve kaliteli ürünlere talep."},
        ],
        "reason": "Bu ülkeler, doğal ve eğitici oyuncaklara yüksek talep duyan, alım gücü yüksek pazarlardır.",
    }

def create_rich_response_for_plastic_toys(data):
    return {
        "recommendation": "Plastik oyuncaklarınız için en uygun potansiyel barındıran ülkeler:",
        "hsCodeInfo": "NLP analizi sonucunda ürününüz için en olası HS Kodu: 9503.00 (Oyuncaklar).",
        "countries": [
            {"name": "Meksika", "volume": 40000000, "reason": "Genç nüfus ve artan orta sınıf."},
            {"name": "Polonya", "volume": 20000000, "reason": "Bölgesel dağıtım merkezi konumu."},
            {"name": "Türkiye", "volume": 15000000, "reason": "Yerel pazar büyüklüğü."},
        ],
        "reason": "Bu ülkeler, rekabetçi fiyatlı ve popüler oyuncaklara yüksek talep duyan pazarlardır.",
    }

def create_rich_response_for_fabric_toys(data):
    return {
        "recommendation": "Kumaş oyuncaklarınız için en uygun potansiyel barındıran ülkeler:",
        "hsCodeInfo": "NLP analizi sonucunda ürününüz için en olası HS Kodu: 9503.00 (Oyuncaklar).",
        "countries": [
            {"name": "Fransa", "volume": 30000000, "reason": "Bebek ürünlerine yüksek talep ve tasarım odaklılık."},
            {"name": "Japonya", "volume": 25000000, "reason": "Kaliteye ve güvenliğe verilen önem."},
            {"name": "Kanada", "volume": 20000000, "reason": "Çevre dostu ve doğal ürünlere ilgi."},
        ],
        "reason": "Bu ülkeler, yumuşak ve güvenli kumaş oyuncaklara özel ilgi duyan pazarlardır.",
    }

# Yeni fonksiyon: Tahmin verisine göre ülke önerisi oluşturma
def get_country_recommendations_for_prediction(product_data):
    category = product_data.get('category', '').lower()
    product_name = product_data.get('product_name_clean', '').lower()

    if "oyuncak" in category or "toys" in product_name:
        # Oyuncaklar için genel öneriler (daha spesifik hale getirilebilir)
        return {
            "recommendation": f"'{product_data.get('product_name_clean', 'Ürün')}' için potansiyel barındıran ülkeler:",
            "hsCodeInfo": "Tahmini HS Kodu: 9503.00 (Oyuncaklar).",
            "countries": [
                {"name": "ABD", "volume": 100000000, "reason": "Büyük pazar ve çeşitli tüketici kitlesi."},
                {"name": "Almanya", "volume": 70000000, "reason": "Kaliteye önem veren bilinçli ebeveynler."},
                {"name": "Japonya", "volume": 40000000, "reason": "Benzersiz ve eğitici oyuncaklara ilgi."},
            ],
            "reason": "Bu ülkeler, genel olarak oyuncak ithalatında yüksek hacme sahiptir ve çeşitli niş pazarlar sunar.",
        }
    elif "elektronik" in category:
        return {
            "recommendation": f"'{product_data.get('product_name_clean', 'Ürün')}' için potansiyel barındıran ülkeler:",
            "hsCodeInfo": "Tahmini HS Kodu: 8500.00 (Elektronik Cihazlar).",
            "countries": [
                {"name": "Çin", "volume": 500000000, "reason": "Üretim ve tüketim merkezi."},
                {"name": "ABD", "volume": 300000000, "reason": "Yüksek teknoloji benimseme oranı."},
                {"name": "Hollanda", "volume": 100000000, "reason": "Avrupa'ya dağıtım merkezi."},
            ],
            "reason": "Elektronik ürünler için küresel talep yüksek olan pazarlardır.",
        }
    # Daha fazla kategori ve ürün bazlı kural eklenebilir
    else:
        # Varsayılan genel öneriler
        return {
            "recommendation": f"'{product_data.get('product_name_clean', 'Ürün')}' için genel potansiyel barındıran ülkeler:",
            "hsCodeInfo": "HS Kodu tahmini için daha fazla bilgiye ihtiyaç var.",
            "countries": [
                {"name": "Almanya", "volume": 150000000, "reason": "Avrupa'nın en büyük ekonomisi ve ithalatçısı."},
                {"name": "ABD", "volume": 200000000, "reason": "Dünyanın en büyük pazarı, yüksek alım gücü."},
                {"name": "Kanada", "volume": 80000000, "reason": "ABD ile güçlü ticaret ilişkileri, istikrarlı pazar."},
            ],
            "reason": "Bu ülkeler, çoğu ürün kategorisi için genel olarak yüksek ithalat potansiyeli sunar.",
        }


# --------------------------
# 5) Chatbot API
# --------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    session_id = request.remote_addr # Basit bir session_id olarak IP adresini kullandık. Daha güvenlisi JWT olabilir.

    if not message.strip():
        return jsonify({"response": "Mesaj boş."})

    response_content = get_chatbot_response_based_on_state(session_id, message)
    
    return jsonify({"response": response_content})


# --------------------------
# 6) ML Prediction API
# --------------------------
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        logging.info(f"Prediction için alınan veri: {data}")
        
        df_input = prepare_dataframe(data)
        prediction = model.predict(df_input)
        
        predicted_price = float(prediction[0])
        
        # Ülke önerilerini al
        country_recommendations = get_country_recommendations_for_prediction(data)
        
        # Yanıtı hem tahmin fiyatını hem de ülke önerilerini içerecek şekilde birleştir
        # Frontend'deki renderRichResponse'un beklediği formatta bir obje döndürüyoruz
        full_response = {
            "predicted_price": predicted_price,
            "recommendation_data": country_recommendations # Ülke önerilerini bu anahtar altında gönderiyoruz
        }
        
        logging.info(f"Tahmin ve Öneri sonucu: {full_response}")
        return jsonify({"response": full_response}) # 'response' anahtarı altında tüm objeyi gönderiyoruz
    except Exception as e:
        logging.error(f"ML tahmini yapılamadı: {e}")
        return jsonify({"error": str(e)}), 400

# --------------------------
# 7) Server Başlat
# --------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)