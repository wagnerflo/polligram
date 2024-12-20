from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from datetime import datetime
from httpx import AsyncClient
from logging import getLogger

logger = getLogger("polligram")
NO_DEFAULT = object()

class Action(ABC):
    @classmethod
    def from_module(self, module, config):
        match getattr(module, "inherit"):
            case "http":
                cls = HTTPAction

            case "html":
                from .html import HTMLAction
                cls = HTMLAction

        return cls(module, config)

    def __init__(self, module, config):
        self.module = module
        self.config = config

    async def fetch(self):
        if iscoroutinefunction(fetch := self.getattr("fetch", None)):
            return await fetch(self)
        else:
            return await self.default_fetch()

    def getattr(self, key, default=NO_DEFAULT):
        if default is NO_DEFAULT:
            return getattr(self.module, key)
        else:
            return getattr(self.module, key, default)

    @abstractmethod
    async def default_fetch(self):
        pass

    async def init(self):
        pass

    async def destroy(self):
        pass

    async def convert(self, raw):
        return raw

    async def disabled(self):
        if iscoroutinefunction(disabled := self.getattr("disabled", None)):
            return await disabled(self)
        return False

    async def run(self):
        if (data := await self.convert(await self.fetch())) is None:
            logger.warning("Fetch returned no data. Not running action.")
            return []
        if action := self.getattr("action", None):
            data = await action(self, data)
        return data

    @property
    def cron(self):
        return self.getattr("cron")

    @property
    def chatid(self):
        return self.config["chatid"]

    @property
    def message_template(self):
        return self.config.get("message", self.getattr("message"))

    @property
    def next_run_time(self):
        return datetime.now() if self.getattr("run_at_start", True) else None

class HTTPAction(Action):
    async def default_fetch(self):
        if iscoroutinefunction(method := self.getattr("method", "GET")):
            method = await method(self)
        if iscoroutinefunction(url := self.getattr("url")):
            url = await url(self)
        if iscoroutinefunction(kwargs := self.getattr("request_kwargs", {})):
            kwargs = await kwargs(self)
        resp = await self.http.request(method, url, **kwargs)
        if resp.status_code != 200:
            logger.warning(f"HTTP request returned status {resp.status_code}.")
            return
        match self.getattr("decode", "text"):
            case "text":
                return resp.text
            case "json":
                return resp.json
            case func if callable(func):
                return func(resp)

    async def init(self):
        self.http = AsyncClient()

    async def destroy(self):
        await self.http.aclose()
