from asyncio import run
from importlib.util import spec_from_file_location, module_from_spec
from logging import (
    getLogger,
    basicConfig as configLogging,
    INFO as LOGGING_INFO,
)
from pathlib import Path
from traceback import print_exc

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from watchfiles import awatch, Change

from .conf import Config
from .db import Database
from .action import Action
from .tg import TelegramClient

logger = getLogger("polligram")

async def run_action(action, glbconf, jobid, tg, db, scheduler):
    if await action.disabled():
        await action.destroy()
        scheduler.remove_job(jobid)
        return

    messages = await action.run()
    hashes = { h for h in db.get_hashes(jobid) }
    update_db = False
    locale = glbconf["LOCALE"]
    debug = glbconf.get("DEBUG", False)

    for msg in messages:
        if msg.hash not in hashes:
            update_db = True
            await tg.send(
                action.chatid,
                msg.format(locale, jobid, action)
            )

    if not debug and update_db:
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

    async def update_jobs(action_name=None):
        if action_name is not None:
            modules.pop(action_name, None)

        async def remove_job(job):
            await job.args[0].destroy()
            job.remove()

        jobids = set()

        for jobid,value in conf.items():
            if jobid == "global":
                continue

            if action_name is not None and value["action"] != action_name:
                continue

            if (job := scheduler.get_job(jobid)) is not None:
                await remove_job(job)

            if (module := load_module(value["action"])) is None:
                continue

            action = Action.from_module(module, value)
            await action.init()

            if await action.disabled():
                continue

            logger.info(f"Adding job: {jobid}.")
            scheduler.add_job(
                run_action,
                trigger=CronTrigger.from_crontab(action.cron),
                args=(action, glb, jobid, tg, db, scheduler),
                id=jobid,
                next_run_time=action.next_run_time,
            )
            jobids.add(jobid)

        for job in scheduler.get_jobs():
            if job.id not in jobids:
                await remove_job(job)

    api_id = glb["API_ID"]
    api_hash = glb["API_HASH"]
    bot_token = glb["BOT_TOKEN"]

    async with TelegramClient(api_id, api_hash, bot_token) as tg:
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
        configLogging(
            level=LOGGING_INFO,
            datefmt="%Y-%m-%d %H:%M:%S",
            format='%(asctime)s [%(name)s] %(message)s',
        )
        run(start())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
