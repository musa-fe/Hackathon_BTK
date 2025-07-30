import streamlit as st
import requests

st.title("🌍 Ürün Fiyat Analizi Chatbotu")

user_input = st.text_input("Ürün adını giriniz:")

if st.button("Tahmin Et"):
    try:
        response = requests.post("http://127.0.0.1:5000/predict", 
                                 json={"product": user_input}).json()
        st.write(f"💡 {user_input} ürünü en pahalı olarak {response['country']} ülkesinde satılabilir. "
                 f"Tahmini fiyat: {response['price']} $")
    except:
        st.write("❌ Backend'e bağlanılamadı. Lütfen önce backend.py dosyasını çalıştırın.")
