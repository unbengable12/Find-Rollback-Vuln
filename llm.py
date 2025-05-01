from google import genai
from google.genai import types

gemini_api_key = 'your gemini api key'

class LLM:
    def __init__(self, model:str = 'gemini-2.0-flash'): # gemini-2.0-flash-lite
        self.client = genai.Client(api_key=gemini_api_key)
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
    


