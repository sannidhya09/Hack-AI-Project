from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("Your API Key")
print("Loaded API Key:", api_key if api_key else "Not found 😢")
