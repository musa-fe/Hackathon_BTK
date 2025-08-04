import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("models/gemini-2.5-pro")

st.title("💬 E-Ticaret Chatbot")
st.write("Ucuz üretim - pahali satiş için akilli öneriler alin.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("✍️ Mesajinizi yazin:")

if st.button("Gönder"):
    if user_input.strip() != "":
        st.session_state.chat_history.append(("Sen", user_input))
        response = model.generate_content(user_input)
        st.session_state.chat_history.append(("Bot", response.text))
    else:
        st.warning("Lütfen bir mesaj yazin.")

for sender, message in st.session_state.chat_history:
    if sender == "Sen":
        st.markdown(f"""
        <div style='text-align:right; background-color:#DCF8C6; color:#000; padding:8px; border-radius:10px; margin:5px; display:inline-block;'>
        🧑 <b>{sender}:</b> {message}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='text-align:left; background-color:#E5E5EA; color:#000; padding:8px; border-radius:10px; margin:5px; display:inline-block;'>
        🤖 <b>{sender}:</b> {message}
        </div>
        """, unsafe_allow_html=True)
