import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("[1/3] API Key loaded successfully.")

if not api_key:
    print("[ERROR] GEMINI_API_KEY not found in .env!")
    exit(1)

client = genai.Client(api_key=api_key)

print("[2/3] Initiating handshake with Mark-1 core...")
models_to_test = ["gemini-3.8-flash", "gemini-flash-latest"]

connected = False
for model_name in models_to_test:
    print(f"--> Testing link with: {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="State in one short sentence that you are online."
        )
        print("\n-------------------------------------------")
        print(f"RESPONSE FROM MARK CORE ({model_name}):")
        print(response.text.strip())
        print("-------------------------------------------\n")
        print(f">> Handshake successful. Core is online using {model_name}.")
        connected = True
        break
    except Exception as e:
        print(f"    [FAILED] {model_name}: {e}")

if not connected:
    print("\n[CRITICAL] All candidate models failed. Check your API key and connection.")