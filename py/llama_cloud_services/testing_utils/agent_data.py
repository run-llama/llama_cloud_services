from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict
import httpx
from ._deterministic import utcnow, hash_schema

if TYPE_CHECKING:
    from .server import FakeLlamaCloudServer


@dataclass
class StoredAgentData:
    data: dict[str, Any]
    id: str
    collection: str
    deployment_name: str

    def __getattr__(self, name: str) -> Any:
        return self.data.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "data":
            super().__setattr__(name, value)
        else:
            self.data[name] = value

    @classmethod
    def from_request_data(cls, data: dict[str, Any]) -> "StoredAgentData":
        return cls(
            data=data.get("data", {}),
            collection=data.get("collection", "default"),
            deployment_name=data.get("deployment_name", ""),
            id=hash_schema(data.get("data", {}))[:7],
        )


def apply_filter(data: dict, filters: dict) -> bool:
    """Check if data matches all filters"""
    ops = {
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "in": lambda a, b: a in b,
        "nin": lambda a, b: a not in b,
    }

    for key, condition in filters.items():
        if key not in data:
            return False

        if isinstance(condition, dict):
            for op, value in condition.items():
                if op in ops:
                    if not ops[op](data[key], value):
                        return False
                else:
                    return False
        else:
            if data[key] != condition:
                return False

    return True


class FakeAgentDataNamespace:
    def __init__(
        self,
        *,
        server: "FakeLlamaCloudServer",
    ) -> None:
        self._server = server
        self.stored: list[StoredAgentData] = []
        self.routes: Dict[str, Any] = {}

    def _create_data(self, request: httpx.Request) -> httpx.Response:
        payload = self._server.json(request=request)
        self.stored.append(StoredAgentData.from_request_data(payload))
        response = {
            "data": payload.get("data", {}),
            "collection": payload.get("collection", "default"),
            "deployment_name": payload.get("deployment_name", ""),
            "created_at": utcnow().isoformat(),
            "updated_at": None,
            "id": hash_schema(payload)[:7],
            "project_id": None,
            "organization_id": None,
        }
        return self._server.json_response(response, status_code=200)

    def _delete_data_by_query(self, request: httpx.Request) -> httpx.Response:
        payload = self._server.json(request=request)
        delete_count = 0
        if (filters := payload.get("filter")) is not None:
            to_keep = []
            for data in self.stored:
                if data.collection == payload.get(
                    "collection", "default"
                ) and data.deployment_name == payload.get("deployment_name"):
                    if not apply_filter(data.data, filters):
                        to_keep.append(data)
                    else:
                        delete_count += 1
            self.stored = to_keep
        return self._server.json_response(
            {"deleted_count": delete_count}, status_code=200
        )

    def _delete_data_by_id(self, request: httpx.Request) -> httpx.Response:
        item_id = request.url.params.get("item_id", None)
        if not item_id:
            return self._server.json_response(
                {
                    "detail": "An item_id path parameter is required to perform this operation"
                },
                status_code=400,
            )
        self.stored = [data for data in self.stored if data.id != item_id]
        return self._server.json_response({}, status_code=200)

    def _get_data_by_id(self, request: httpx.Request) -> httpx.Response:
        item_id = request.url.params.get("item_id", None)
        payload = self._server.json(request=request)
        if not item_id:
            return self._server.json_response(
                {
                    "detail": "An item_id path parameter is required to perform this operation"
                },
                status_code=400,
            )
        data = [data for data in self.stored if data.id == item_id]
        if data:
            response = {
                "data": data[0].data,
                "collection": payload.get("collection", "default"),
                "deployment_name": payload.get("deployment_name", ""),
                "created_at": utcnow().isoformat(),
                "updated_at": None,
                "id": hash_schema(payload)[:7],
                "project_id": None,
                "organization_id": None,
            }
            return self._server.json_response(response, status_code=200)
        else:
            return self._server.json_response(
                {"detail": f"No data with ID: {item_id}"}, status_code=404
            )

    def _search_data(self, request: httpx.Request) -> httpx.Response:
        payload = self._server.json(request=request)
        found = []
        if (filters := payload.get("filter")) is not None:
            for data in self.stored:
                if data.collection == payload.get(
                    "collection", "default"
                ) and data.deployment_name == payload.get("deployment_name"):
                    if apply_filter(data.data, filters):
                        found.append(
                            {
                                "data": data.data,
                                "collection": data.collection,
                                "deployment_name": data.deployment_name,
                                "created_at": utcnow().isoformat(),
                                "updated_at": None,
                                "id": data.id,
                                "project_id": None,
                                "organization_id": None,
                            }
                        )
        return self._server.json_response(
            {"items": found, "next_page_token": None, "total_size": len(found)},
            status_code=200,
        )

    def _update_data(self, request: httpx.Request) -> httpx.Response:
        item_id = request.url.params.get("item_id", None)
        payload = self._server.json(request=request)
        if not item_id:
            return self._server.json_response(
                {
                    "detail": "An item_id path parameter is required to perform this operation"
                },
                status_code=400,
            )
        for i, data in enumerate(self.stored):
            if data.id == item_id:
                data.data = payload.get("data", data.data)
                self.stored[i] = data
        response = {
            "data": payload.get("data", {}),
            "collection": payload.get("collection", "default"),
            "deployment_name": payload.get("deployment_name", ""),
            "created_at": utcnow().isoformat(),
            "updated_at": None,
            "id": item_id,
            "project_id": None,
            "organization_id": None,
        }
        return self._server.json_response(response, status_code=200)

    def _aggregate_data(self, request: httpx.Request) -> httpx.Response:
        payload = self._server.json(request=request)
        add_count = payload.get("count", False)
        group_bys: list[str] = payload.get("group_by", [])
        groups: dict[str, list[dict[str, Any]]] = {key: [] for key in group_bys}
        if (filters := payload.get("filter")) is not None:
            for data in self.stored:
                if data.collection == payload.get(
                    "collection", "default"
                ) and data.deployment_name == payload.get("deployment_name"):
                    if apply_filter(data.data, filters):
                        for key in group_bys:
                            if key in data.data:
                                groups[key].append(data.data)
        response: dict[str, Any] = {
            "items": [],
            "next_page_token": None,
            "total_size": 0,
        }
        for k in groups:
            if groups[k]:
                first_item = groups[k][0]
            else:
                first_item = None
            response["items"].append(
                {
                    "group_key": k,
                    "first_item": first_item,
                    "count": len(groups[k]) if add_count else None,
                }
            )
        response["total_size"] = len(response["items"])
        return self._server.json_response(response, status_code=200)

    def register(self) -> None:
        server = self._server
        route = server.add_route(
            "POST",
            "/api/v1/beta/agent-data",
            self._create_data,
            namespace="create_item",
        )
        self.routes["stateless_run"] = route
        self.stateless_run = route
        server.add_route(
            "POST",
            "/api/v1/beta/agent-data/:aggregate",
            self._aggregate_data,
            namespace="untyped_aggregate",
            alias="aggregate",
        )
        server.add_route(
            "POST",
            "/api/v1/beta/agent-data/:delete",
            self._delete_data_by_query,
            namespace="delete",
        )
        server.add_route(
            "POST",
            "/api/v1/beta/agent-data/:search",
            self._search_data,
            namespace="untyped_search",
            alias="search",
        )
        server.add_route(
            "DELETE",
            "/api/v1/beta/agent-data/:item_id",
            self._delete_data_by_id,
            namespace="delete_item",
        )
        server.add_route(
            "GET",
            "/api/v1/beta/agent-data/:item_id",
            self._get_data_by_id,
            namespace="untyped_get_item",
            alias="get_item",
        )
        server.add_route(
            "PUT",
            "/api/v1/beta/agent-data/:item_id",
            self._update_data,
            namespace="update_item",
        )
