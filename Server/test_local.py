import asyncio
from core.agents.graph_chat import stream_chat
from core.agents.chat_history import chat_db

async def test():
    chat_db.clear_history()
    print("History cleared.")
    
    user_text = "What does the User class do?"
    chat_db.add_message("user", user_text)
    
    history = chat_db.get_history()
    
    print("Streaming...")
    full_response = ""
    async for token in stream_chat(user_text, history, None):
        print(token, end="", flush=True)
        full_response += token
        
    chat_db.add_message("assistant", full_response)
    print("\n\nDone.")

asyncio.run(test())
