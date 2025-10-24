from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List


app = FastAPI()


# In-memory storage for messages and active connections
db_messages = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        self.active_connections.pop(username, None)

    async def send_personal_message(self, message: str, username: str):
        websocket = self.active_connections.get(username)
        if websocket:
            await websocket.send_text(message)

manager = ConnectionManager()



class Message(BaseModel):
    sender: str
    receiver: str
    content: str


class TypingEvent(BaseModel):
    sender: str
    receiver: str
    event: str  # should be 'typing'






# WebSocket endpoint for real-time chat and typing events
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # If it's a typing event
            if data.get("event") == "typing":
                typing_event = TypingEvent(**data)
                await manager.send_personal_message(
                    f"{typing_event.sender} is typing...", typing_event.receiver
                )
            # Otherwise, treat as message
            else:
                message = Message(**data)
                db_messages.append(message)
                await manager.send_personal_message(
                    f"{message.sender}: {message.content}", message.receiver
                )
    except WebSocketDisconnect:
        manager.disconnect(username)
