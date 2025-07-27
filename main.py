import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import whisper
from elevenlabs import generate
import json
import re
from typing import Dict, List
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()

# Twilio setup
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

# Whisper model
model = whisper.load_model("base")

# In-memory storage for orders
orders = []

# Pydantic model for order submission
class Order(BaseModel):
    name: str
    order_list: List[str]

@app.post("/submit_order")
async def submit_order(order: Order):
    try:
        order_id = len(orders) + 1
        eta = "15-20 minutes"
        orders.append({"id": order_id, "name": order.name, "order_list": order.order_list, "eta": eta})
        with open("orders.json", "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False)
        return {"order_id": order_id, "eta": eta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Intent detection and response logic
def detect_intent(text: str) -> Dict[str, any]:
    text = text.lower()
    if any(keyword in text for keyword in ["order", "طلب", "sipariş"]):
        return {"intent": "order", "entities": extract_order_items(text)}
    elif any(keyword in text for keyword in ["complaint", "شكوى", "şikayet"]):
        return {"intent": "complaint", "entities": {}}
    elif any(keyword in text for keyword in ["question", "سؤال", "soru"]):
        return {"intent": "question", "entities": {}}
    return {"intent": "unknown", "entities": {}}

def extract_order_items(text: str) -> Dict[str, List[str]]:
    items = re.findall(r"(chicken|دجاج|shawarma|شاورما|fries|بطاطس)", text, re.IGNORECASE)
    return {"items": items}

def generate_response(intent: Dict[str, any], language: str = "ar-SY") -> str:
    if intent["intent"] == "order":
        items = intent["entities"].get("items", [])
        if items:
            if language == "ar-SY":
                return f"شكراً على طلبك! طلبت: {', '.join(items)}. بيتم تأكيد الطلب قريباً."
            elif language == "en":
                return f"Thank you for your order! You ordered: {', '.join(items)}. Order will be confirmed soon."
            elif language == "tr":
                return f"Siparişiniz için teşekkürler! Sipariş ettiniz: {', '.join(items)}. Sipariş yakında onaylanacak."
        return "ممكن توضح وش تبغى تطلب؟" if language == "ar-SY" else "Please clarify what you want to order." if language == "en" else "Lütfen ne sipariş etmek istediğinizi belirtin."
    elif intent["intent"] == "complaint":
        return "آسفين على أي إزعاج! ممكن توضح الشكوى ونحلها فوراً؟" if language == "ar-SY" else "Sorry for any inconvenience! Can you clarify the complaint?" if language == "en" else "Herhangi bir rahatsızlık için üzgünüz! Şikayeti açıklayabilir misiniz?"
    elif intent["intent"] == "question":
        return "أي سؤال عندك؟ جاهزين نساعد!" if language == "ar-SY" else "Any questions? We're here to help!" if language == "en" else "Sorunuz mu var? Yardımcı olmaya hazırız!"
    return "ما فهمت، ممكن توضح أكثر؟" if language == "ar-SY" else "I didn't understand, can you clarify?" if language == "en" else "Anlamadım, daha fazla açıklayabilir misiniz?"

@app.post("/simulate_call")
async def simulate_call(audio: UploadFile = File(...)):
    try:
        with open("temp_audio.wav", "wb") as f:
            f.write(await audio.read())
        return await handle_recording("temp_audio.wav")
    except Exception as e:
        return {"error": str(e)}

async def handle_recording(audio_path: str):
    resp = VoiceResponse()
    try:
        result = model.transcribe(audio_path, language="ar")
        text = result["text"]
        logger.info(f"Transcribed text: {text}")

        intent = detect_intent(text)
        response_text = generate_response(intent)

        audio_response = generate(
            text=response_text,
            voice="Adam",  # Free-tier Arabic voice; replace with Syrian-specific for production
            model="eleven_multilingual_v2"
        )

        with open("response.mp3", "wb") as f:
            f.write(audio_response)

        with open("conversation_log.json", "a", encoding="utf-8") as f:
            json.dump({"text": text, "intent": intent, "response": response_text}, f, ensure_ascii=False)
            f.write("\n")
        return {"response_text": response_text, "audio_path": "response.mp3"}
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        resp.say("عذراً، فيه مشكلة. حاول مرة ثانية.", language="ar-XA")
        return str(resp)