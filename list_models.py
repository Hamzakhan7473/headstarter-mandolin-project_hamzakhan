import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load your .env file where GEMINI_API_KEY is stored
load_dotenv()

# Configure the Gemini client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# List and print all available models
models = genai.list_models()
for model in models:
    print(model.name)
