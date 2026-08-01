from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RoomCreate(BaseModel):
    name:        str
    topic:       Optional[str] = None
    max_members: int           = 10

    class Config:
        json_schema_extra = {
            "example": {
                "name":        "DSA Mentorship - Batch 3",
                "topic":       "Data Structures & Algorithms",
                "max_members": 15
            }
        }

class RoomUpdate(BaseModel):
    name:        Optional[str]  = None
    topic:       Optional[str]  = None
    max_members: Optional[int]  = None
    is_active:   Optional[bool] = None


class RoomResponse(BaseModel):
    id:             str
    name:           str
    topic:          Optional[str]
    mentor_id:      str
    mentor_name:    str
    mentor_picture: str
    member_count:   int
    max_members:    int
    invite_code:    str
    invite_link:    str
    is_active:      bool
    last_message:   Optional[str]
    created_at:     datetime

class RoomPreviewResponse(BaseModel):
    id:             str
    name:           str
    topic:          Optional[str]
    mentor_name:    str
    mentor_picture: str
    member_count:   int
    max_members:    int
    is_active:      bool


class MessageCreate(BaseModel):
    content:    str
    attachment: Optional[str] = None

class MessageResponse(BaseModel):
    id:             str
    sender_id:      str
    sender_name:    str
    sender_picture: str
    content:        str
    attachment:     Optional[str]
    sent_at:        datetime
    read_by_count:  int


def build_invite_link(invite_code: str) -> str:
    return f"https://vssutvibes.in/rooms/join/{invite_code}"


def room_to_response(room: dict) -> dict:
    messages     = room.get("messages", [])
    last_message = messages[-1]["content"] if messages else None
    return {
        "id":             str(room["_id"]),
        "name":           room["name"],
        "topic":          room.get("topic"),
        "mentor_id":      room["mentor_id"],
        "mentor_name":    room["mentor_name"],
        "mentor_picture": room["mentor_picture"],
        "member_count":   len(room.get("members", [])),
        "max_members":    room["max_members"],
        "invite_code":    room["invite_code"],
        "invite_link":    build_invite_link(room["invite_code"]),
        "is_active":      room["is_active"],
        "last_message":   last_message,
        "created_at":     room["created_at"],
    }


def message_to_response(msg: dict, index: int) -> dict:
    return {
        "id":             str(index),
        "sender_id":      msg["sender_id"],
        "sender_name":    msg["sender_name"],
        "sender_picture": msg["sender_picture"],
        "content":        msg["content"],
        "attachment":     msg.get("attachment"),
        "sent_at":        msg["sent_at"],
        "read_by_count":  len(msg.get("read_by", [])),
    }