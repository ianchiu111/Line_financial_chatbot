import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv(".env")

class LLMClient:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
            verbose=False,
        )
        
    def invoke(self, messages):
        return self.llm(messages)