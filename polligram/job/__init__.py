from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from hashlib import blake2b
from httpx import AsyncClient

NO_DEFAULT = object()

class Job(AbstractAsyncContextManager, ABC):
    @classmethod
    def from_module(self, jobid, module, config):
        match getattr(module, "type"):
            case "html":
                from .html import HTMLJob
                cls = HTMLJob

        return cls(jobid, module, config)

    def __init__(self, jobid, module, config):
        self.jobid = jobid
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

    async def convert(self, raw):
        return raw

    async def action(self):
        res = await self.getattr("action")(
            await self.convert(
                await self.fetch()
            )
        )
        if self.getattr("with_hash", False):
            return res
        else:
            return {
                blake2b(msg.encode("utf-8")).hexdigest(): msg
                for msg in res
            }

    @property
    def cron(self):
        return self.getattr("cron")

    @property
    def next_run_time(self):
        return datetime.now() if self.getattr("run_at_start", True) else None

class HTTPJob(Job):
    async def default_fetch(self):
        resp = await self.client.request(
            self.getattr("method", "GET"),
            self.getattr("url"),
            **self.getattr("request_kwargs", {})
        )
        match self.getattr("decode", "text"):
            case "text":
                return resp.text
            case "json":
                return resp.json

    async def __aenter__(self):
        self.client = AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()
