@app.websocket("/chat/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"📞 WebSocket connection opened for call {call_id}")
    
    # Step 1: Send session ready event so Retell knows to start audio
    await websocket.send_json({
        "type": "session.update",
        "status": "ready"
    })
    
    # Step 2: Send immediate greeting using correct event type
    await websocket.send_json({
        "type": "response.output_text",
        "text": "Hi! Thanks for calling. This is your receptionist speaking. How can I help today?"
    })
    
    try:
        while True:
            caller_input = await websocket.receive_text()
            print(f"🎤 Caller said: {caller_input}")
            
            # Send caller input to GPT for a fast, natural reply
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
                "type": "response.output_text",
                "text": reply
            })
    except Exception as e:
        print(f"❌ WebSocket closed for call {call_id}: {e}")
