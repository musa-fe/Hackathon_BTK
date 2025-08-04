import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("gemini-pro")

st.set_page_config(page_title="E-Ticaret Chatbot", page_icon="🤖")

st.title("💬 E-Ticaret Chatbot")
st.write("Ucuz uretim - pahali satis icin akilli oneriler alin.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("Mesajinizi yazin:", key="user_input")

if st.button("Gonder"):
    if user_input.strip() != "":
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        response = model.generate_content(user_input)
        st.session_state.chat_history.append({"role": "bot", "content": response.text})

for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(f"""
        <div style='text-align:right; background-color:#DCF8C6; padding:8px; border-radius:10px; margin:5px; display:inline-block;'>
        🧑 <b>Sen:</b> {msg['content']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='text-align:left; background-color:#E5E5EA; padding:8px; border-radius:10px; margin:5px; display:inline-block;'>
        🤖 <b>Bot:</b> {msg['content']}
        </div>
        """, unsafe_allow_html=True)
