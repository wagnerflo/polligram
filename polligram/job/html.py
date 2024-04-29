from bs4 import BeautifulSoup
from . import HTTPJob

class HTMLJob(HTTPJob):
    async def convert(self, raw):
        return BeautifulSoup(raw, "html5lib")
