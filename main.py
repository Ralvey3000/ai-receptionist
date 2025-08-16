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
        return {"status": "success", "sample_reply": response.choices[0].message.content}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Simple HTTP fallback for text testing
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
                {"role": "system", "content": "You are a warm, professional legal receptionist. Keep responses short, natural, and never give legal advice."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        print("Error in chat endpoint:", str(e))
        return {"reply": "Hi there! Thanks for calling. How can I help you today?"}

# WebSocket for Retell Custom LLM Voice: use delta format
@app.websocket("/chat/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"📞 WebSocket connection opened for call {call_id}")

    # Session handshake: include audio (and text for compatibility)
    session_update = {
        "type": "session.update",
        "modalities": ["output_audio", "output_text"],
        "status": "ready"
    }
    await websocket.send_json(session_update)
    print(f"🔄 Sent session.update handshake: {session_update}")

    # Send greeting using delta flow
    greeting_id = "greeting"
    await websocket.send_json({
        "type": "response.create",
        "response_id": greeting_id,
        "modalities": ["output_audio", "output_text"]
    })
    await websocket.send_json({
        "type": "response.output_text.delta",
        "response_id": greeting_id,
        "delta": "Hi! Thanks for calling. This is your receptionist. How can I help today?"
    })
    await websocket.send_json({
        "type": "response.output_text.done",
        "response_id": greeting_id
    })
    print("🔄 Sent greeting sequence")

    reply_counter = 0

    try:
        while True:
            # Retell sends JSON-as-text frames; we log raw to keep it simple
            caller_message = await websocket.receive_text()
            print(f"🎤 Incoming frame: {caller_message}")

            # Only respond when Retell flags response_required
            if '"interaction_type":"response_required"' not in caller_message:
                # Ignore partial/update_only frames etc.
                continue

            # Generate reply with OpenAI
            gpt_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a warm, professional legal receptionist. Keep replies short, natural, and never provide legal advice."},
                    {"role": "user", "content": caller_message}
                ]
            )
            reply_text = gpt_response.choices[0].message.content.strip()
            print(f"🤖 AI reply: {reply_text}")

            reply_counter += 1
            reply_id = f"reply_{reply_counter}"

            # Delta sequence for Retell to synthesize voice
            await websocket.send_json({
                "type": "response.create",
                "response_id": reply_id,
                "modalities": ["output_audio", "output_text"]
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
            print(f"🔄 Sent delta sequence for {reply_id}")

            # Optional: explicitly end the agent turn
            await websocket.send_json({
                "type": "turn.end",
                "turn_type": "agent_turn"
            })
            print("🔚 Sent turn.end for agent_turn")

    except Exception as e:
        print(f"❌ WebSocket closed for call {call_id}: {e}")
