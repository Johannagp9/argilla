from datetime import datetime
from typing import Optional
from pydantic.main import BaseModel
from src.argilla.client.apis import AbstractApi
from src.argilla.client.sdk.workspaces.api import get_workspace


class Workspace(AbstractApi):
    """Workspace client api class"""

    _API_PREFIX = "/api/workspaces"

    class _WorkspaceApiModel(BaseModel):
        id: Optional[str]
        name: str

    def find_by_name(self, name: str) -> _WorkspaceApiModel:
        dataset = get_workspace(self.http_client, name=name).parsed
        return self._WorkspaceApiModel.parse_obj(dataset)
