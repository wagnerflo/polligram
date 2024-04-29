from asyncio import run
from contextlib import AsyncExitStack
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from tomllib import load as decode_toml
from traceback import print_exc

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from watchfiles import awatch, Change

from .db import Database
from .job import Job
from .tg import TelegramClient

async def run_action(job, tg, db):
    hashes = { h for h in db.get_hashes(job.jobid) }
    messages = await job.action()
    update_db = False

    for h,msg in messages.items():
        if h not in hashes:
            update_db = True
            await tg.send(job.config["chatid"], msg)

    if update_db:
        db.set_hashes(job.jobid, messages.keys())

async def watch_actions(conf, stack, scheduler, tg, db):
    base = Path("actions").resolve()

    async def handle_change(change, path):
        if not path.match("*.py"):
            return

        base = path.with_suffix("").name
        base_prefix = f"{base}:"

        def is_job_instance(jobid):
            return jobid == base or jobid.startswith(base_prefix)

        for job in scheduler.get_jobs():
            if is_job_instance(job.id):
                job.remove()

        if change == Change.deleted:
            return

        try:
            spec = spec_from_file_location(path.stem, path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)

            for key,value in conf.items():
                if is_job_instance(key):
                    job = await stack.enter_async_context(
                        Job.from_module(key, module, value)
                    )
                    scheduler.add_job(
                        run_action,
                        trigger=CronTrigger.from_crontab(job.cron),
                        args=(job, tg, db),
                        id=job.jobid,
                        next_run_time=job.next_run_time,
                    )
        except:
            print_exc()

    for path in base.iterdir():
        await handle_change(Change.added, path)

    async for changes in awatch(base, recursive=False):
        for change,path in changes:
            await handle_change(change, Path(path))

async def start():
    with open(f"{__package__}.toml", "rb") as fp:
        conf = decode_toml(fp)

    scheduler = AsyncIOScheduler()
    scheduler.start()

    async with ( AsyncExitStack() as stack,
                 TelegramClient(conf["API_ID"], conf["API_HASH"]) as tg ):
        await watch_actions(
            conf, stack, scheduler, tg, Database(tg.storage.conn)
        )

def main():
    try:
        run(start())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
