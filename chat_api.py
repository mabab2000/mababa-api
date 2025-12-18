from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import asyncpg
from pathlib import Path
import logging

# load .env into environment (if present)
load_dotenv()


app = FastAPI()

# Allow CORS from any origin for HTTP endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# --- Student models and DB helpers ---

class StudentIn(BaseModel):
    firstname: str
    lastname: str
    mothername: Optional[str] = None
    fathername: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None


class StudentOut(StudentIn):
    id: int


async def init_db_pool():
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    pool = await asyncpg.create_pool(database_url)
    return pool


@app.on_event("startup")
async def on_startup():
    try:
        pool = await init_db_pool()
        app.state.db_pool = pool

        # apply SQL migrations if file exists
        mig_path = Path("migrations/schema.sql")
        if mig_path.exists():
            try:
                sql = mig_path.read_text(encoding="utf-8")
                async with pool.acquire() as conn:
                    # execute migration SQL (CREATE TABLE IF NOT EXISTS ...)
                    await conn.execute(sql)
                    logging.info("Applied migrations/schema.sql")
            except Exception as e:
                logging.warning(f"Failed to apply migrations/schema.sql: {e}")
    except Exception as e:
        # If DB not configured or connection failed, keep app running but without DB features
        logging.warning(f"Database pool init failed: {e}")
        app.state.db_pool = None


@app.on_event("shutdown")
async def on_shutdown():
    pool = getattr(app.state, "db_pool", None)
    if pool:
        await pool.close()






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


# HTTP endpoints for students


@app.post("/students", status_code=201)
async def create_student(student: StudentIn):
    pool = getattr(app.state, "db_pool", None)
    if not pool:
        raise HTTPException(status_code=500, detail="Database not configured")

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO students(firstname, lastname, mothername, fathername, age, gender) VALUES($1,$2,$3,$4,$5,$6)",
            student.firstname,
            student.lastname,
            student.mothername,
            student.fathername,
            student.age,
            student.gender,
        )

    return {"message": "Student registration successful"}


@app.get("/students", response_model=List[StudentOut])
async def get_students():
    pool = getattr(app.state, "db_pool", None)
    if not pool:
        raise HTTPException(status_code=500, detail="Database not configured")
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, firstname, lastname, mothername, fathername, age, gender FROM students ORDER BY id")
    return [dict(r) for r in rows]
