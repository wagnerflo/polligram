from bs4 import BeautifulSoup
from . import HTTPAction

class HTMLAction(HTTPAction):
    async def convert(self, raw):
        return BeautifulSoup(raw, "html5lib")
