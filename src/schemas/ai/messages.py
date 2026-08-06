from pydantic import BaseModel
from datetime import datetime

class IncomingMessage(BaseModel):
    client_id: str
    channel: str
    text: str
    timestamp: datetime
    client_name: str | None

class OutgoingMessage(BaseModel):
    client_id: str
    channel: str
    text: str
    reply_to: str | None