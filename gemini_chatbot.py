import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("API KEY:", os.getenv("GOOGLE_API_KEY"))


model = genai.GenerativeModel("models/gemini-2.5-pro")

response = model.generate_content("Merhaba Gemini! Bana selam ver.")

print("Gemini'den gelen cevap:")
print(response.text)



while True:
    soru = input("Siz: ")
    if soru.lower() in ["çik", "exit", "q"]:
        break
    yanit = model.generate_content(soru)
    print("Gemini:", yanit.text)
