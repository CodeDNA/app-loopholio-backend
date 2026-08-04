import os
from pydantic import SecretStr
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai").lower()
OPENAI_MODEL = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o-mini")

def get_llm(provider: str = DEFAULT_PROVIDER, temperature: float = 0):
    provider = provider.lower()
    
    if provider == "openai":
        open_ai_api = os.getenv("OPENAI_API_KEY")
        if not open_ai_api:
            raise ValueError("OPENAI_API_KEY not found in the environment.")
        return ChatOpenAI(
            model=OPENAI_MODEL, 
            api_key=SecretStr(open_ai_api),
            temperature=temperature
        )
        
    elif provider == "gemini":
        gemini_api = os.getenv("GOOGLE_API_KEY")
        if not gemini_api:
            raise ValueError("GEMINI_API_KEY not found in the environment.")
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            api_key=gemini_api,
            temperature=temperature
        )
        
    else:
        raise ValueError(f"Unsupported LLM provider: '{provider}'. Choose 'openai' or 'gemini'.")