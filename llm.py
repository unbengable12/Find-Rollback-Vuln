from google import genai
from google.genai import types
from constants import GEMINI_API_KEY

class LLM:
    def __init__(self, model:str = 'gemini-2.0-flash'): # gemini-2.0-flash-lite
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = model
        self.should_reason = False

    def prompt(self, prompt:str, temperature:float = 0.0):
        response = self.client.models.generate_content(
            model = self.model,
            contents = [prompt],
            config = types.GenerateContentConfig(
                temperature=temperature
            )
        )
        return response.text
    


