from babel.dates import get_month_names
from datetime import date,datetime
from json import loads as json_decode
from polligram import Msg
from re import (
    compile as regex,
    search as re_search,
    MULTILINE, VERBOSE, DOTALL,
)
from zoneinfo import ZoneInfo

inherit = "http"
cron = "0,30 * * * *"
message = '''
{{ jobid }}: {{ room }} für {{ max_persons }} \
{% if with_breakfast %}mit{% else %}ohne{% endif %} Frühstück. \
{% if cancellation_date %}\
Stornierbar bis {{ fdatetime(cancellation_date) }}\
{% else %}\
Nicht stornierbar\
{% endif %}. \
Preis {{ fprice(price) }}.
'''

TZ = ZoneInfo("Europe/Berlin")
MONTH_NAMES = {
    v:k for k,v in get_month_names("wide", locale="de_DE").items()
}
LIST_RE = regex(r"^b_rooms_available_and_soldout: (.*),$", MULTILINE)

async def disabled(job):
    return date.today() > job.config["checkin"]

async def url(job):
    return f'https://www.booking.com/hotel/{job.config["hotel"]}'

async def request_kwargs(job):
    return dict(
        params={
            "checkin": job.config["checkin"],
            "checkout": job.config["checkout"],
            "group_adults": job.config.get("adults", 2),
            "group_children": job.config.get("children", 0),
            "no_rooms": job.config.get("rooms", 1),
            "lang": "de-de",
            "selected_currency": "EUR",
        },
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) "
                "Gecko/20100101 Firefox/129.0"
            ),
        },
        cookies=job.config.get("cookies", {}),
        follow_redirects=True,
    )

async def action(job, html):
    num_people = job.config.get("adults", 2) + job.config.get("children", 0)
    only_with_breakfast = job.config.get("only_with_breakfast", True)
    only_free_cancellation = job.config.get("only_free_cancellation", False)
    only_cheapest = job.config.get("only_cheapest", True)
    results = []

    for room in json_decode(LIST_RE.search(html).group(1)):
        for block in room["b_blocks"]:
            if block["b_max_persons"] < num_people:
                continue

            skip = False
            room_id,*rest = block["b_block_id"].split("_")
            cancellation_type = block["b_cancellation_type"]
            mealplan = block["b_mealplan_included_name"]
            price = float(block["b_raw_price"])

            match mealplan:
                case "breakfast":
                    with_breakfast = True
                case None:
                    with_breakfast = False
                    if only_with_breakfast:
                        skip = True
                case _:
                    raise Exception(
                        f"Unknown b_mealplan_included_name={mealplan}"
                    )

            match cancellation_type:
                case "non_refundable" | "special_condition":
                    cancelation_date = None
                    if only_free_cancellation:
                        skip = True
                case "free_cancellation":
                    res = re_search(
                        rf"""
                        data-block-id="{room_id}_
                        .*
                        Kostenlose\ Stornierung</strong>
                        \ vor
                        (?:\ (\d\d):(\d\d)\ Uhr)?
                        \ (?:am|dem)
                        \ (\d{{1,2}})\.\ ([^ ]+)\ (\d{{4}})
                        .*
                        name="nr_rooms_{room_id}
                        """,
                        html,
                        VERBOSE | DOTALL
                    )
                    hour,minute,day,month,year = res.groups()
                    cancelation_date = datetime(
                        int(year), MONTH_NAMES[month], int(day),
                        int(hour or 0), int(minute or 0), tzinfo=TZ,
                    )
                case _:
                    raise Exception(
                        f"Unknown b_cancellation_type={cancellation_type}"
                    )

            if not skip:
                results.append(
                    Msg(
                        f"{block['b_block_id']}={price}",
                        room=room["b_name"],
                        max_persons=block["b_max_persons"],
                        price=price,
                        cancellation_date=cancelation_date,
                        with_breakfast=with_breakfast,
                    )
                )

    results = sorted(results, key=lambda i: i.price)

    if only_cheapest:
        if only_free_cancellation:
            results = results[0:1]
        else:
            results = [
                next(filter(lambda i: not bool(i.cancellation_date), results)),
                next(filter(lambda i: bool(i.cancellation_date), results)),
            ]

    return results
