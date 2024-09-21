from datetime import datetime
from polligram import *

inherit = "html"
cron = "0 3 * * *"
url = "https://plagwitzer-markthalle.de"
message = '''
{{ jobid }} {{ fdate(dt) }} {{ time }}: \
<a href="{{ href }}">{{ text }}</a>
'''

ignore = (
    "Egenberger Lebensmittel",
    "Samstagsmarkt",
)

def rmsp(s):
    return s.replace("\xa0", " ").replace("\u2009", "").replace("\xad", "")

def find_events(soup):
    for evt in soup.find_all(class_="calendar__event"):
        title = evt.find(class_="calendar__event-title")
        text = rmsp(title.text)

        if text in ignore:
            continue

        time = evt.find("time")
        dt = datetime.fromisoformat(time["datetime"])
        yield (
            dt,
            Msg(
                dt.isoformat(),
                dt=dt,
                time=rmsp(time.text),
                href=title["href"],
                text=text,
            )
        )

async def action(job, soup):
    return [ msg for _,msg in sorted(find_events(soup)) ]
