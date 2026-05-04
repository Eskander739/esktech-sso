from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    redirect_uris: str
