from abc import ABC, abstractmethod


class RewriteProvider(ABC):
    @abstractmethod
    async def rewrite(self, *, model: str, mode: str, text: str, api_key: str, **kwargs) -> str:
        raise NotImplementedError
