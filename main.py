from fastapi import FastAPI, Request, WebSocket
from openai import OpenAI
import os

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
    
    # Step 1: Send session ready event so Retell knows to start audio
    await websocket.send_json({
        "type": "session.update",
        "status": "ready"
    })
    
    # Step 2: Send immediate greeting
    await websocket.send_json({
        "type": "output_text",
        "text": "Hi! Thanks for calling. This is your receptionist speaking. How can I help today?"
    })
    
    try:
        while True:
            caller_input = await websocket.receive_text()
            print(f"🎤 Caller said: {caller_input}")
            
            gpt_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a warm, professional receptionist. Respond like a real person: short, natural sentences, small pauses, friendly tone."},
                    {"role": "user", "content": caller_input}
                ]
            )
            
            reply = gpt_response.choices[0].message.content
            print(f"🤖 AI reply: {reply}")
            
            # Send GPT reply to Retell in correct voice output format
            await websocket.send_json({
                "type": "output_text",
                "text": reply
            })
    except Exception as e:
        print(f"❌ WebSocket closed for call {call_id}: {e}")
