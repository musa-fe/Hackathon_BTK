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
gemini_model = genai.GenerativeModel("models/gemini-1.5-flash") 

# --------------------------
# 3) ML Modelini ve Veri Setini Yükle
# --------------------------
# Sizin orijinal dosya yolu tanımlamalarını koruyoruz
MODEL_PATH = "model/model.joblib"
FEATURES_PATH = "model/feature_columns.json"
DATA_FILE_PATH = "synthetic_ecommerce_data.xlsx" 

model = None
feature_cols = None
ecommerce_df = None # E-ticaret veri setini global olarak tanımlıyoruz
product_names_data = {} # Ürün isimlerini ve ilgili verilerini saklayacak sözlük

try:
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(f"Model dosyası bulunamadı: {MODEL_PATH}")
    if not Path(FEATURES_PATH).exists():
        raise FileNotFoundError(f"feature_columns.json dosyası bulunamadı: {FEATURES_PATH}")
    if not Path(DATA_FILE_PATH).exists(): 
        raise FileNotFoundError(f"Veri dosyası bulunamadı: {DATA_FILE_PATH}. Lütfen dosya adının ve uzantısının doğru olduğundan emin olun.")

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    
    # Dosya uzantısına göre doğru okuma fonksiyonunu seçiyoruz
    if DATA_FILE_PATH.endswith('.csv'):
        ecommerce_df = pd.read_csv(DATA_FILE_PATH)
    elif DATA_FILE_PATH.endswith('.xlsx'):
        ecommerce_df = pd.read_excel(DATA_FILE_PATH)
    else:
        raise ValueError("Desteklenmeyen veri dosyası uzantısı. Lütfen .csv veya .xlsx kullanın.")

    # product_name sütunundaki verileri hazırlama
    # product_name_clean sütunu varsa onu kullan, yoksa product_name kullan
    product_name_col = 'product_name_clean' if 'product_name_clean' in ecommerce_df.columns else 'product_name'
    
    # Her bir ürün adı için ilgili kategori, marka, ülke vb. bilgileri sakla
    # İlk eşleşen satırı alacak şekilde ayarlıyoruz
    for index, row in ecommerce_df.iterrows():
        product_name_lower = str(row[product_name_col]).lower()
        if product_name_lower not in product_names_data:
            product_names_data[product_name_lower] = {
                'product_id': str(row['product_id']), # product_id'yi de ekleyelim
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


    logging.info("ML Model, feature kolonları ve e-ticaret veri seti başarıyla yüklendi.")
    logging.info(f"Yüklenen benzersiz ürün adı sayısı: {len(product_names_data)}")

except FileNotFoundError as e:
    logging.error(f"Dosya yükleme hatası: {e}. Lütfen tüm gerekli dosyaların doğru yerde olduğundan emin olun.")
    exit(1)
except Exception as e:
    logging.error(f"Model, feature kolonları veya veri seti yüklenirken beklenmeyen bir hata oluştu: {e}")
    exit(1)

# --------------------------
# Chatbot state yönetimi
# --------------------------
chat_state = {}  # session_id: {stage: int, data: dict}
MAX_CHAT_HISTORY = 10 # Örnek için bir limit belirledik

# --------------------------
# 4) Yardımcı Fonksiyonlar
# --------------------------
def prepare_dataframe(data: dict):
    """JSON verisini DataFrame'e çevir ve kolonları hizala"""
    df = pd.DataFrame([data])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = None # Eğer kolonda veri yoksa None atar
    return df[feature_cols]

def get_country_recommendations_for_prediction(product_data, ecommerce_df, model, feature_cols):
    # CSV'deki benzersiz ülkeleri alıyoruz
    all_possible_countries = ecommerce_df['country'].unique().tolist()
    
    predictions_per_country = []

    # Temel girdi verisini kopyala ve 'country' ile 'country_clean' alanlarını çıkar
    base_input_for_model = product_data.copy()
    base_input_for_model.pop('country', None)
    base_input_for_model.pop('country_clean', None) 
    
    # Varsayılan değerleri ayarla (frontend'den gelmeyenler için)
    base_input_for_model['city'] = base_input_for_model.get('city', None)
    base_input_for_model['seller'] = base_input_for_model.get('seller', None)
    base_input_for_model['stock'] = base_input_for_model.get('stock', 100) # Varsayılan stok
    base_input_for_model['platform'] = base_input_for_model.get('platform', "E-commerce") # Varsayılan platform
    base_input_for_model['month'] = base_input_for_model.get('month', pd.Timestamp.now().month) # Mevcut ay

    for country in all_possible_countries:
        current_product_input = base_input_for_model.copy()
        current_product_input['country'] = country
        
        df_sample = prepare_dataframe(current_product_input)
        
        try:
            pred_price = model.predict(df_sample)[0] 
            predictions_per_country.append({
                "name": country,
                "volume": round(float(pred_price), 2), 
                "reason": f"Bu ülkede tahmini satış fiyatı: {round(float(pred_price), 2)} USD."
            })
        except Exception as e:
            logging.warning(f"'{country}' için tahmin yapılamadı: {e}")

    predictions_per_country.sort(key=lambda x: x["volume"], reverse=True)
    top_n_countries = predictions_per_country[:5] 

    hs_code_info = "HS Kodu tahmini için daha fazla bilgiye ihtiyaç var."
    if product_data.get('category', '').lower() == 'oyuncak':
        hs_code_info = "Tahmini HS Kodu: 9503.00 (Oyuncaklar)."
    elif product_data.get('category', '').lower() == 'elektronik':
        hs_code_info = "Tahmini HS Kodu: 8500.00 (Elektronik Cihazlar)."

    return {
        "recommendation": f"'{product_data.get('product_name_clean', 'Ürün')}' için en yüksek fiyat potansiyeli olan ülkeler:",
        "hsCodeInfo": hs_code_info,
        "countries": top_n_countries,
        "reason": "Bu ülkeler, girdiğiniz ürün özellikleri için en yüksek tahmini satış fiyatına sahip pazarlardır."
    }

# ML Tahminini yapan ve zengin yanıtı döndüren yardımcı fonksiyon
def perform_ml_prediction_and_get_rich_response(product_data):
    try:
        # Frontend'den gelen 'country' değeri için doğrudan tahmin yap
        df_input_for_single_country = prepare_dataframe(product_data)
        predicted_price_for_input_country = model.predict(df_input_for_single_country)[0]
        
        # Tüm olası ülkeler için tahminleri al ve sırala
        country_recommendations = get_country_recommendations_for_prediction(product_data, ecommerce_df, model, feature_cols)
        
        full_response = {
            "predicted_price": float(predicted_price_for_input_country), 
            "recommendation_data": country_recommendations 
        }
        return full_response
    except Exception as e:
        logging.error(f"perform_ml_prediction_and_get_rich_response içinde ML tahmini yapılamadı: {e}")
        # Hata durumunda bir hata objesi döndürüyoruz
        return {"error": str(e), "message": "Fiyat tahmini yapılırken bir hata oluştu."}


# --------------------------
# Chatbot Mantığı
# --------------------------
def get_chatbot_response_based_on_state(session_id, user_message):
    global chat_state
    
    current_state = chat_state.get(session_id, {'stage': 0, 'data': {}})
    stage = current_state['stage']
    data = current_state['data']
    response = ""
    
    user_message_lower = user_message.lower()

    # Eğer kullanıcı bir önceki adımda fiyat tahmini onayı bekliyorsa
    if stage == 'awaiting_prediction_confirmation':
        if user_message_lower in ["evet", "yes", "tahmin et", "fiyat"]:
            if 'product_data_for_prediction' in data:
                # Kaydedilmiş ürün verilerini kullanarak tahmini yap
                rich_response_data = perform_ml_prediction_and_get_rich_response(data['product_data_for_prediction'])
                if "error" in rich_response_data:
                    response = f"Üzgünüm, fiyat tahmini yapılırken bir sorun oluştu: {rich_response_data['message']}" # Hata mesajını kullan
                else:
                    response = rich_response_data
                chat_state[session_id] = {'stage': 0, 'data': {}} # Tahmin sonrası state'i sıfırla
            else:
                response = "Üzgünüm, hangi ürün için tahmin yapacağımı bulamadım. Lütfen ürün adını tekrar belirtin."
                chat_state[session_id] = {'stage': 0, 'data': {}}
        else:
            response = "Anladım, fiyat tahmini yapmak istemiyorsunuz. Başka bir ürün veya konuda yardımcı olabilirim."
            chat_state[session_id] = {'stage': 0, 'data': {}} # State'i sıfırla

    # Adım 0: Giriş veya genel sohbet (veya yeni bir ürün araması)
    elif stage == 0:
        found_product_data = None
        for product_name_key, details in product_names_data.items():
            # Kullanıcının mesajının ürün adını içerip içermediğini kontrol et
            # Tam eşleşme yerine 'in' operatörü ile kısmi eşleşme yapıyoruz
            if product_name_key in user_message_lower:
                found_product_data = details
                break
        
        if found_product_data:
            # Ürün bulundu, detayları kullanarak yanıt ver ve tahmini onayı bekle
            product_name = found_product_data['product_name_clean']
            category = found_product_data['category']
            brand = found_product_data['brand']
            country = found_product_data['country'] 

            response_text = (
                f"Verilerimde **'{product_name}'** ürününü buldum!\n\n"
                f"Bu ürün **'{category}'** kategorisinde, **'{brand}'** markasına ait ve genellikle **'{country}'** ülkesinde satılıyor.\n\n"
                "Bu ürün için fiyat tahmini almak ister misiniz? Lütfen 'Evet' yazarak devam edin veya aşağıdaki formu kullanın."
            )
            response = response_text
            # Ürün verilerini state'e kaydet ve aşamayı değiştir
            chat_state[session_id] = {
                'stage': 'awaiting_prediction_confirmation',
                'data': {'product_data_for_prediction': found_product_data}
            }
        
        # Eğer ürün bulunamadıysa ve "toys" veya "oyuncak" ise özel akış
        elif "toys" in user_message_lower or "oyuncak" in user_message_lower:
            response = "Harika bir ürün! Daha doğru bir öneri için lütfen birkaç soruya cevap verin. Ürününüzün ana malzemesi nedir? (örn: ahşap, plastik, kumaş)"
            chat_state[session_id] = {'stage': 1, 'data': {'product_type': 'toys'}}
        
        # Hiçbiri değilse, genel Gemini yanıtı
        else:
            try:
                context_prompt = (
                    "Sen bir ihracat ve ürün analizi chatbotusun. Amacın, kullanıcılara ürünleri hakkında bilgi vermek ve pazar analizi yapmak için gerekli detayları toplamaktır. "
                    "Kullanıcı bir ürün veya sektör adı belirttiğinde, eğer daha fazla detaya ihtiyacın varsa (örn: ürünün tipi, malzemesi, kullanım amacı, modeli, yaş grubu gibi spesifik özellikler), bu detayları sorarak yanıtını zenginleştirmeye çalış. "
                    "Yanıtını kısa paragraflara veya madde işaretlerine ayır ve mümkünse çok uzun tutma."
                )
                prompt_for_gemini = f"{context_prompt}\n\nKullanıcı sorusu: {user_message}"
                gemini_response = gemini_model.generate_content(prompt_for_gemini)
                response = gemini_response.text
            except Exception as e:
                logging.error(f"Gemini API hatası: {e}")
                response = "Üzgünüm, Gemini ile iletişim kurarken bir sorun oluştu."
    
    # Adım 1: Malzeme sorusu (oyuncaklar için)
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
        
        # Frontend'den gelen 'country' değeri için doğrudan tahmin yap
        df_input_for_single_country = prepare_dataframe(data)
        predicted_price_for_input_country = model.predict(df_input_for_single_country)[0]
        
        # Tüm olası ülkeler için tahminleri al ve sırala
        country_recommendations = get_country_recommendations_for_prediction(data, ecommerce_df, model, feature_cols)
        
        # Yanıtı hem tahmin fiyatını hem de ülke önerilerini içerecek şekilde birleştir
        full_response = {
            "predicted_price": float(predicted_price_for_input_country), # Formda girilen ülke için fiyat
            "recommendation_data": country_recommendations # Diğer ülkeler için öneriler
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