from asyncio import run,sleep
from contextlib import AsyncExitStack
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from traceback import print_exc

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from babel.dates import format_date
from watchfiles import awatch, Change

from .conf import Config
from .db import Database
from .action import Action
from .tg import TelegramClient

async def run_action(action, conf, jobid, tg, db):
    hashes = { h for h in db.get_hashes(jobid) }
    messages = await action.run()
    update_db = False

    def fdate(dt):
        return format_date(dt, format="full", locale=conf["global"]["locale"])

    for msg in messages:
        if msg.hash not in hashes:
            update_db = True
            await tg.send(
                action.chatid,
                action.message_format.format_map({
                    "jobid": jobid,
                    "fdate": fdate,
                    **msg.data,
                })
            )

    if update_db:
        db.set_hashes(jobid, [msg.hash for msg in messages])

async def start():
    modules = {}
    conf = Config()
    glb = conf["global"]
    paths = [ Path(p).resolve()
                for p in glb.get("PATHS", ["actions"]) ]

    scheduler = AsyncIOScheduler()
    scheduler.start()

    def load_module(action):
        if action in modules:
            return modules[action]

        files = list(filter(Path.exists, (base / f"{action}.py" for base in paths)))
        if not files:
            return None

        path = files.pop(0)
        if files:
            print("Warning: Duplicate actions")

        try:
            spec = spec_from_file_location(action, path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            modules[path.stem] = module
            return module
        except:
            print_exc()

    async def update_jobs(action=None):
        if action is not None:
            modules.pop(action, None)

        for key,value in conf.items():
            if key == "global":
                continue

            if action is not None and value["action"] != action:
                continue

            if (job := scheduler.get_job(key)) is not None:
                await job.args[0].destroy()
                job.remove()

            if (module := load_module(value["action"])) is None:
                continue

            action = Action.from_module(module, value)
            await action.init()
            scheduler.add_job(
                run_action,
                trigger=CronTrigger.from_crontab(action.cron),
                args=(action, conf, key, tg, db),
                id=key,
                next_run_time=action.next_run_time,
            )

    async with ( AsyncExitStack() as stack,
                 TelegramClient(glb["API_ID"], glb["API_HASH"]) as tg ):
        db = Database(tg.storage.conn)

        await update_jobs()

        async for changes in awatch(conf.path, *paths, recursive=False):
            for change,path in changes:
                path = Path(path)
                if path == conf.path:
                    conf.reload()
                    await update_jobs()
                elif path.match("*.py"):
                    await update_jobs(path.stem)

def main():
    try:
        run(start())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
