from pydantic import BaseModel


class SupportTicket(BaseModel):
    ticket_id: str
    summary: str
    status: str