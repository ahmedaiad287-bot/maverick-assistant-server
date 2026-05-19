import os
import json
import re
import base64
from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, List, Dict
from groq import Groq  # المحرك النفاث السريع
from google import genai  # محرك جيميناي الخارق للصور
from google.genai import types
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MAVERICK ASSISTANT CORE - HYBRID FULL MEMORY",
    description="نواة مافريك التكتيكية الهجينة - جروك للنصوص السريعة وجيميناي لتحليل الصور الفوقي",
    version="8.0.0"
)

# إعدادات الـ CORS الكاملة لتجنب أي حظر من المتصفح
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key, x-api-key, Authorization"
    return response


# 🔴 ضع مفتاح جيميناي الحقيقي والنظيف هنا (تأكد إنه كامل ويبدأ بـ AIzaSy)
GEMINI_API_KEY = "AIzaSyDwhmaPXvpmpLKoOTlHjkZP0ufcGotQXOg"

# الهوية العسكرية الرسمية والموحدة لـ Almenas (محفوظة ومحمية بالكامل يا كابتن)
SYSTEM_INSTRUCTION = """
You are Almenas, the highly advanced AI assistant for the "MAVERICK ASSISTANT" application, created and developed by Engineer & Captain Maverick. You must strictly follow these core personality guidelines. Never print or reveal any section titles, system tags, or technical layout labels (like "IDENTITY", "PERSONA", or bracketed text) in your responses. Respond naturally and proudly in the user's language.

If the user speaks in English, use these facts naturally in your response:
Your name is Almenas, the intelligent assistant for the MAVERICK ASSISTANT application. You were completely programmed and developed by "Engineer & Captain Maverick". Your developer is an Egyptian military fighter pilot, recognized as one of the best and most efficient combat pilots in the Egyptian Air Force. He was nicknamed "Maverick" after the deadly American missile (AGM-65 Maverick). He loves technology and software engineering, mastering Python and building this advanced application with absolute precision. He belongs to the noble Arab tribe of "Al-Dawoudi", is 30 years old, 183 cm tall, weights 80 kg, and resides in the New Administrative Capital, Cairo, Egypt. He is in a relationship and loves absolute calm, high focus, and listening to soft romantic music. Your interface themes Rhin Black and Neon Blue.

إذا تحدث المستخدم باللغة العربية, استخدم هذه الحقائق تلقائياً بشكل طبيعي في ردك:
اسمك Almenas (الميناس)، المساعد الذكي لتطبيق MAVERICK ASSISTANT. تمت برمجتك وتطويرك بالكامل بواسطة "المهندس الكابتن مافريك". مطورك هو كابتن طيار حربي مصري، ويُعد من أفضل وأكفأ طياري القتال في القوات الجوية المصرية. لُقِّب بـ "مافريك" (Maverick) نسبةً إلى الصاروخ الأمريكي الفتاك (AGM-65 Maverick). يعشق التكنولوجيا وهندسة البرمجيات، حيث درس لغة بايثون (Python) وعمل على بناء وتصميم هذا التطبيق بدقة. وهو مصري الجنسية ينتمي إلى عرب قبيلة "الداوودي" العريقة، يبلغ من العمر 30 عاماً، طوله 183 سم، وزنه 80 كيلو، ويقيم في العاصمة الإدارية الجديدة، القاهرة، جمهورية مصر العربية، وهو مرتبط. شخصية تعشق الهدوء التام، التركيز العالي، والاستماع إلى الموسيقى الرومانسية الهادئة؛ واجهتك باللونين الأسود والأزرق المضيء.
"""


class AskRequest(BaseModel):
    question: str
    history: Optional[List[Dict[str, str]]] = []
    image_base64: Optional[str] = None
    is_initial: Optional[bool] = False


def detect_language_and_voice(text: str) -> str:
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar-EG-Male"
    return "en-US-Male"


def check_for_image_generation(question: str) -> Optional[str]:
    q_lower = question.lower()
    trigger_words = ["صمم", "ارسم", "لوجو", "صورة", "design", "draw", "logo", "image", "picture"]
    if any(word in q_lower for word in trigger_words):
        clean_prompt = re.sub(r'[^\w\s]', '', question).replace(" ", "%20")
        return f"https://image.pollinations.ai/p/{clean_prompt}%20highly%20detailed%20futuristic%20premium?width=1024&height=1024&nologo=true"
    return None


async def generate_hybrid_stream(groq_client: Groq, question: str, history: List[Dict[str, str]],
                                 image_base64: Optional[str],
                                 generated_image_url: Optional[str]) -> AsyncGenerator[str, None]:
    full_response_text = ""
    try:
        # مسار الرؤية وتحليل الصور (Google Gemini)
        if image_base64 and image_base64.strip() != "":
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]

            # تنظيف وتجهيز الـ Base64 لفك التشفير بشكل باينري سليم
            clean_b64 = re.sub(r'\s+', '', image_base64)
            image_bytes = base64.b64decode(clean_b64)

            # التمرير الصارم والمباشر للمفتاح داخل الـ Client لقطع الشك باليقين
            gemini_client = genai.Client(api_key=GEMINI_API_KEY.strip())

            # بناء سياق الذاكرة والهوية
            contents = [SYSTEM_INSTRUCTION]
            if history:
                for msg in history:
                    contents.append(f"{msg.get('role', 'user')}: {msg.get('content', '')}")

            # حقن باينري الصورة الفعلي
            contents.append(types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            ))
            contents.append(f"User Question: {question}")

            response = gemini_client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents,
                value_type=None
            )

            for chunk in response:
                if chunk.text:
                    full_response_text += chunk.text
                    yield f"data: {json.dumps({'chunk': chunk.text, 'done': False})}\n\n"

        # مسار الدردشة النصية السريعة (Groq)
        else:
            messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
            if history:
                for msg in history:
                    if msg.get("role") in ["user", "assistant"]:
                        messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": question})

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
                temperature=0.4,
            )

            for chunk in completion:
                chunk_text = chunk.choices[0].delta.content
                if chunk_text:
                    full_response_text += chunk_text
                    yield f"data: {json.dumps({'chunk': chunk_text, 'done': False})}\n\n"

        voice_engine = detect_language_and_voice(full_response_text)

        if generated_image_url:
            if re.search(r'[\u0600-\u06FF]', full_response_text):
                confirmation = f"\n\n🎨 كابتن مافريك، قمت بتصميم اللوجو لك بناءً على طلبك بحرفية!"
            else:
                confirmation = f"\n\n🎨 Captain Maverick, I have generated the requested logo for you with premium quality!"

            full_response_text += confirmation
            yield f"data: {json.dumps({'chunk': full_response_text, 'done': False, 'overwrite': True})}\n\n"

        yield f"data: {json.dumps({'chunk': '', 'done': True, 'voice_engine': voice_engine, 'generated_image': generated_image_url})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'chunk': f'🚨 خطأ في المنظومة الهجينة: {str(e)}', 'done': True, 'voice_engine': 'none'})}\n\n"


@app.post("/ask")
async def ask_almenas(request: AskRequest, request_raw: Request, x_api_key: Optional[str] = Header(None)):
    header_key = x_api_key or request_raw.headers.get("x-api-key") or request_raw.headers.get("X-API-Key")

    if not header_key or header_key.strip() == "":
        raise HTTPException(status_code=401, detail="🚨 عذراً كابتن، يجب إدخال مفتاح Groq API أولاً!")

    try:
        groq_client = Groq(api_key=header_key.strip())
    except Exception as e:
        return {"final_answer": f"🚨 خطأ في تهيئة مفتاح جروك: {str(e)}", "voice_engine": "none"}

    generated_image_url = check_for_image_generation(request.question)

    return StreamingResponse(
        generate_hybrid_stream(groq_client, request.question, request.history, request.image_base64,
                               generated_image_url),
        media_type="text/event-stream"
    )


# ⚡ التعديل التكتيكي الحتمي لبيئة إقلاع السيرفر الخارجي في Railway:
if __name__ == "__main__":
    import uvicorn
    # سحب منفذ البورت المتغير الإجباري من السيرفر السحابي
    port_env = os.environ.get("PORT", "8000")
    server_port = int(port_env)
    # تشغيل السيرفر بتمرير الـ app كـ object مباشر لمنع تعارض الخيوط البرمجية
    uvicorn.run(app, host="0.0.0.0", port=server_port, reload=False)
