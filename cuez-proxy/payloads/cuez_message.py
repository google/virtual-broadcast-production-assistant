from typing import Any
from pydantic import BaseModel, Field

class CuezRequest(BaseModel):
    path: str | None = Field(
        default=None, 
        title="The name of the CUEZ path to send request to",
        example= "trigger/next"
    )

class CuezResponse(BaseModel):
    response: Any | None = Field(
        default=None, 
        title="Response Dict from the Cuez API"
    )