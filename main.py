from fastapi import FastAPI, Request, WebSocket
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

@app.websocket("/chat/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"📞 WebSocket connection opened for call {call_id}")

    # ✅ Send session update handshake (only output_audio)
    session_update = {
        "type": "session.update",
        "modalities": ["output_audio"],
        "status": "ready"
    }
    await websocket.send_json(session_update)
    print(f"🔄 Sent session.update handshake: {session_update}")

    # ✅ Greeting via `instructions`
    await websocket.send_json({
        "type": "response.create",
        "response_id": "greeting",
        "modalities": ["output_audio"],
        "instructions": "Hi! Thanks for calling. This is your receptionist speaking. How can I help today?"
    })
    print("🔄 Sent greeting via instructions")

    reply_counter = 0

    try:
        while True:
            caller_message = await websocket.receive_text()
            print(f"🎤 Caller said: {caller_message}")

            if '"interaction_type":"update_only"' in caller_message:
                print("ℹ️ Ignoring update_only event")
                continue

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

            reply_counter += 1
            reply_id = f"reply_{reply_counter}"

            # ✅ Send reply using simplified instructions format
            await websocket.send_json({
                "type": "response.create",
                "response_id": reply_id,
                "modalities": ["output_audio"],
                "instructions": reply_text
            })
            print(f"🔄 Sent instructions for {reply_id}")

            # ✅ Optional: End the agent's turn
            await websocket.send_json({
                "type": "turn.end",
                "turn_type": "agent_turn"
            })
            print("🔚 Sent turn.end for agent_turn")

    except Exception as e:
        print(f"❌ WebSocket closed for call {call_id}: {e}")
