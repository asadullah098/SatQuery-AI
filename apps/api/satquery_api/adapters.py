import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ModelRequest:
    asset_ids: list[str]
    query: str
    task: str


@dataclass(frozen=True)
class ModelResponse:
    answer: str
    confidence: float
    warning: str


class VisionLanguageModelAdapter(Protocol):
    model_id: str
    version: str

    def predict(self, request: ModelRequest) -> ModelResponse: ...


class MockRSInternVLAdapter:
    model_id = "rs-internvl-s1-s2"
    version = "unverified-mock"

    def predict(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            answer="The paired observations indicate water-dominant regions in the central and south-eastern zones.",
            confidence=0.87,
            warning="Mock result: RS-InternVL checkpoint inference has not run.",
        )


class RemoteModelAdapter:
    model_id = "rs-internvl-s1-s2"
    version = "remote-unverified"

    def __init__(self, endpoint: str, token: str | None = None, timeout: float = 120.0) -> None:
        self.endpoint, self.token, self.timeout = endpoint.rstrip("/"), token, timeout

    def predict(self, request: ModelRequest) -> ModelResponse:
        body = json.dumps({"asset_ids": request.asset_ids, "query": request.query, "task": request.task}).encode()
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(Request(f"{self.endpoint}/predict", body, headers, method="POST"), timeout=self.timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError("Remote model worker is unavailable") from error
        return ModelResponse(answer=str(payload["answer"]), confidence=float(payload.get("confidence", 0)), warning=str(payload.get("warning", "Remote score is uncalibrated.")))


def configured_adapter() -> tuple[VisionLanguageModelAdapter, str]:
    mode = os.getenv("SATQUERY_INFERENCE_MODE", "deterministic").lower()
    endpoint = os.getenv("SATQUERY_MODEL_WORKER_URL")
    if mode == "remote" and endpoint:
        return RemoteModelAdapter(endpoint, os.getenv("SATQUERY_MODEL_WORKER_TOKEN")), "remote"
    return MockRSInternVLAdapter(), "mock" if mode == "mock" else "deterministic"
