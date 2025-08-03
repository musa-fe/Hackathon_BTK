import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# API anahtarını yükle
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Modeli başlat
model = genai.GenerativeModel("gemini-pro")

st.set_page_config(page_title="E-Ticaret Chatbot", page_icon="🤖")

st.title("💬 E-Ticaret Chatbot")
st.write("Ucuz üretim - pahalı satış için öneriler alın.")

# Kullanıcı girişi
user_input = st.text_input("Mesajınızı yazın:")

if st.button("Gönder"):
    if user_input.strip() != "":
        response = model.generate_content(user_input)
        st.markdown(f"**Bot:** {response.text}")
    else:
        st.warning("Lütfen bir mesaj yazın.")
