import streamlit as st
import json
import requests
import whisper
from elevenlabs import generate
import soundfile as sf
import numpy as np
import os

st.title("Syrian Arabic Voice Agent Testing UI")

model = whisper.load_model("base")

audio_file = st.file_uploader("Upload Audio (Syrian Arabic)", type=["wav", "mp3"])
text_input = st.text_area("Or Type in Syrian Arabic")

if audio_file or text_input:
    if audio_file:
        audio_data, sample_rate = sf.read(audio_file)
        result = model.transcribe(audio_data, language="ar")
        transcribed_text = result["text"]
    else:
        transcribed_text = text_input

    st.write(f"**Transcribed Input**: {transcribed_text}")

    def detect_intent(text):
        text = text.lower()
        if any(keyword in text for keyword in ["order", "طلب", "sipariş"]):
            return {"intent": "order", "entities": {"items": []}}
        elif any(keyword in text for keyword in ["complaint", "شكوى", "şikayet"]):
            return {"intent": "complaint", "entities": {}}
        return {"intent": "unknown", "entities": {}}

    intent = detect_intent(transcribed_text)
    st.write(f"**Detected Intent**: {intent['intent']}")
    st.write(f"**Entities**: {intent['entities']}")

    def generate_response(intent):
        if intent["intent"] == "order":
            return "شكراً على طلبك! بيتم تأكيد الطلب قريباً."
        return "ما فهمت، ممكن توضح أكثر؟"

    response_text = generate_response(intent)
    st.write(f"**Agent Response**: {response_text}")

    audio_response = generate(
        text=response_text,
        voice="Adam",  # Free-tier Arabic voice
        model="eleven_multilingual_v2"
    )
    st.audio(audio_response, format="audio/mp3")

st.subheader("Conversation Logs")
if os.path.exists("conversation_log.json"):
    with open("conversation_log.json", "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f]
    for log in logs:
        st.write(f"Input: {log['text']}, Intent: {log['intent']}, Response: {log['response']}")