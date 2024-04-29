from pyrogram import Client
from pyrogram.enums import ParseMode
from os import getcwd

class TelegramClient(Client):
    def __init__(self, api_id, api_hash):
        super().__init__(__package__, api_id, api_hash, workdir=getcwd())

    async def send(self, chatid, msg):
        return await self.send_message(
            chatid, msg,
            parse_mode=ParseMode.HTML,
        )
