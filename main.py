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
            "sample_reply": response.choices[0].message["content"]
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ✅ Chat endpoint for Retell
@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message", "")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are a professional, friendly legal receptionist. Greet callers warmly, collect their name, phone number, case type, and escalate urgent matters by tagging them as 'URGENT'. Never provide legal advice."
            },
            {"role": "user", "content": user_message}
        ]
    )

    reply = response.choices[0].message["content"]
    return {"reply": reply}
