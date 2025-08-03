import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("models/gemini-2.5-pro")

st.set_page_config(page_title="E-Ticaret Chatbot", page_icon="🤖")

st.title("💬 E-Ticaret Chatbot")
st.write("Ucuz uretim - pahali satis icin oneriler alin.")

user_input = st.text_input("Mesajinizi yazin:")

if st.button("Gonder"):
    if user_input.strip() != "":
        response = model.generate_content(user_input)
        st.markdown(f"**Bot:** {response.text}")
    else:
        st.warning("Lutfen bir mesaj yazin.")
