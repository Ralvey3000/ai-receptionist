from fastapi import FastAPI, Request
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
        # Quick test to check OpenAI connection
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

# ✅ Chat endpoint for Retell
@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        # Log the full incoming request for debugging
        data = await request.json()
        print("Incoming Retell request:", data)

        # Extract message safely (Retell might send a different field)
        user_message = data.get("message") or data.get("input") or ""

        if not user_message:
            # No message yet? Start with greeting
            return {"reply": "Hello! Thank you for calling. How may I assist you today?"}

        # Call GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional, friendly legal receptionist. Start every call by warmly greeting the caller and asking their name and phone number."
                },
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        print("Error in chat endpoint:", str(e))
        # Always respond with a greeting so Retell doesn't hang up
        return {"reply": "Hello! Thank you for calling. How may I assist you today?"}
