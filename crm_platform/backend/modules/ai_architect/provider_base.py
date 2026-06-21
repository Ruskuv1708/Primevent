from __future__ import annotations

from abc import ABC, abstractmethod


class ArchitectProvider(ABC):
    @abstractmethod
    def generate_blueprint(self, owner_messages: list[str]) -> dict:
        raise NotImplementedError

    @abstractmethod
    def generate_proposals(self, blueprint: dict) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def generate_refinement(
        self,
        message: str,
        artifacts: dict,
        blueprint: dict | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        raise NotImplementedError
