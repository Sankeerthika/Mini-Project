import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import google.generativeai as genai
except ImportError:
    print("google-generativeai not installed"); sys.exit(1)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

key = os.getenv("GOOGLE_GEMINI_API_KEY", "")
if not key or "your_gemini" in key:
    print("No real GOOGLE_GEMINI_API_KEY set"); sys.exit(2)

genai.configure(api_key=key)

try:
    models = list(genai.list_models())
except Exception as e:
    print(f"Failed to list models: {type(e).__name__}: {e}")
    sys.exit(3)

print(f"Total models: {len(models)}")
print("Models with generateContent support (name only):")
for m in models:
    name = getattr(m, "name", "") or ""
    methods = list(getattr(m, "supported_generation_methods", None) or [])
    if "generateContent" in methods or not methods:
        # print short model name after models/
        short = name.split("/")[-1] if "/" in name else name
        print(f"  - {short}   ({name})")
