from datetime import datetime
from babel.dates import format_date

type = "html"
cron = "0 3 * * *"
url = "https://plagwitzer-markthalle.de"

ignore = (
    "Egenberger Lebensmittel",
    "Samstagsmarkt",
)

def fdate(dt):
    return format_date(dt, format="full", locale="de_DE")

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
            f"{fdate(dt)} {rmsp(time.text)}: "
            f"<a href=\"{title["href"]}\">{text}</a>",
        )

async def action(soup):
    return [text for _,text in sorted(find_events(soup))]
