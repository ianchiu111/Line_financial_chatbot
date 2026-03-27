import io
import os
import openai
from dotenv import load_dotenv
load_dotenv(".env")

def transcribe_audio(audio_bytes: io.BytesIO) -> str:
    """
    >>>>> Temporary
    - Use openai api first. Next will use trianed-model to replace it.
    """
    audio_bytes.name = "audio.m4a"
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_bytes,
    )
    return result.text