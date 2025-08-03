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
    
    # Send session ready
    session_ready = {"type": "session.update", "status": "ready"}
    print("🔄 Sending:", session_ready)
    await websocket.send_json(session_ready)
    
    # Greeting response
    greeting_id = "greeting"
    greeting_create = {"type": "response.create", "response_id": greeting_id}
    print("🔄 Sending:", greeting_create)
    await websocket.send_json(greeting_create)
    
    greeting_delta = {"type": "response.output_text.delta", "response_id": greeting_id, "delta": "Hi! Thanks for calling. This is your receptionist speaking. How can I help today?"}
    print("🔄 Sending:", greeting_delta)
    await websocket.send_json(greeting_delta)
    
    greeting_done = {"type": "response.output_text.done", "response_id": greeting_id}
    print("🔄 Sending:", greeting_done)
    await websocket.send_json(greeting_done)
    
    try:
        while True:
            caller_input = await websocket.receive_text()
            print(f"🎤 Caller said: {caller_input}")
            
            gpt_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a warm, professional receptionist. Keep responses short, natural, and human-like."},
                    {"role": "user", "content": caller_input}
                ]
            )
            reply = gpt_response.choices[0].message.content
            print(f"🤖 AI reply: {reply}")
            
            # Create new response for GPT reply
            reply_id = "reply"
            reply_create = {"type": "response.create", "response_id": reply_id}
            print("🔄 Sending:", reply_create)
            await websocket.send_json(reply_create)
            
            # Send reply delta
            reply_delta = {"type": "response.output_text.delta", "response_id": reply_id, "delta": reply}
            print("🔄 Sending:", reply_delta)
            await websocket.send_json(reply_delta)
            
            # Mark reply done
            reply_done = {"type": "response.output_text.done", "response_id": reply_id}
            print("🔄 Sending:", reply_done)
            await websocket.send_json(reply_done)
            
    except Exception as e:
        print(f"❌ WebSocket closed for call {call_id}: {e}")
