from fastapi import FastAPI, Request, WebSocket
from openai import OpenAI
import os

# Create the FastAPI app
app = FastAPI()

# Create OpenAI client using API key from Railway environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Test route to confirm Railway is working
@app.get("/")
def root():
    return {"message": "✅ AI Receptionist server is running on Railway!"}

@app.get("/test")
def test_openai():
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, AI receptionist!"}]
        )
        return {
            "status": "success",
            "sample_reply": response.choices[0].message.content
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ✅ Chat endpoint (for fallback HTTP POST requests)
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        print("Incoming Retell HTTP request:", data)
        user_message = data.get("message") or data.get("input") or ""
        
        if not user_message:
            return {"reply": "Hi there! Thanks for calling. How can I help you today?"}
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a warm, professional receptionist. Sound natural, keep responses short, and make the caller feel comfortable."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        print("Error in chat endpoint:", str(e))
        return {"reply": "Hi there! Thanks for calling. How can I help you today?"}

# ✅ WebSocket endpoint for Retell Realtime Voice
@app.websocket("/chat/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"📞 WebSocket connection opened for call {call_id}")

    # 🔄 Send correct session handshake for audio
    session_update = {
        "type": "session.update",
        "modalities": ["output_audio", "output_text"],  # Add both
        "status": "ready"
    }
    await websocket.send_json(session_update)
    print(f"🔄 Sent session.update handshake: {session_update}")

    # 🔊 Send greeting (response.create + delta + done)
    greeting_id = "greeting"
    await websocket.send_json({
        "type": "response.create",
        "response_id": greeting_id,
        "modalities": ["output_audio"]
    })
    await websocket.send_json({
        "type": "response.output_text.delta",
        "response_id": greeting_id,
        "delta": "Hi! Thanks for calling. This is your receptionist speaking. How can I help today?"
    })
    await websocket.send_json({
        "type": "response.output_text.done",
        "response_id": greeting_id
    })
    print("🔄 Sent greeting sequence")

    reply_counter = 0

    try:
        while True:
            caller_message = await websocket.receive_text()
            print(f"🎤 Caller said: {caller_message}")

            # Ignore update_only events
            if '"interaction_type":"update_only"' in caller_message:
                print("ℹ️ Ignoring update_only event")
                continue

            # Only respond to response_required
            if '"interaction_type":"response_required"' not in caller_message:
                continue

            # Generate GPT reply
            gpt_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a warm, professional receptionist. Keep responses short, natural, and human-like."},
                    {"role": "user", "content": caller_message}
                ]
            )
            reply_text = gpt_response.choices[0].message.content
            print(f"🤖 AI reply: {reply_text}")

            # Unique response_id
            reply_counter += 1
            reply_id = f"reply_{reply_counter}"

            # Send GPT reply (response.create + delta + done)
            await websocket.send_json({
                "type": "response.create",
                "response_id": reply_id,
                "modalities": ["output_audio"]
            })
            await websocket.send_json({
                "type": "response.output_text.delta",
                "response_id": reply_id,
                "delta": reply_text
            })
            await websocket.send_json({
                "type": "response.output_text.done",
                "response_id": reply_id
            })
            print(f"🔄 Sent reply sequence for {reply_id}")

    except Exception as e:
        print(f"❌ WebSocket closed for call {call_id}: {e}")

