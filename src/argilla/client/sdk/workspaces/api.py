from functools import lru_cache
from typing import Union

from argilla.client.sdk.client import AuthenticatedClient
from argilla.client.sdk.commons.errors_handler import handle_response_error
from argilla.client.sdk.commons.models import Response
from argilla.client.sdk.workspaces.models import Workspace
import httpx
from argilla.client.sdk.commons.models import (
    ErrorMessage,
    HTTPValidationError,
    Response,
)


@lru_cache(maxsize=None)
def get_workspace(
        client: AuthenticatedClient,
        name: str,
) -> Response[Workspace]:
    url = "{}/api/workspaces/{name}".format(client.base_url, name=name)

    response = httpx.get(
        url=url,
        headers=client.get_headers(),
        cookies=client.get_cookies(),
        timeout=client.get_timeout(),
    )

    return _build_response(response=response, name=name)


def _build_response(response: httpx.Response, name: str) -> Response[
    Union[Workspace, ErrorMessage, HTTPValidationError]]:
    if response.status_code == 200:
        parsed_response = Workspace(**response.json())
        return Response(
            status_code=response.status_code,
            content=response.content,
            headers=response.headers,
            parsed=parsed_response,
        )
    return handle_response_error(response, dataset=name)
