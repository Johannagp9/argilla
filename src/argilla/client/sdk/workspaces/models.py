from typing import List, Optional
from pydantic import BaseModel


class Workspace(BaseModel):
    id: str
    name: str
