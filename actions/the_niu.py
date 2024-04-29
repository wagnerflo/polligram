from datetime import timedelta
from re import compile as regex
from polligram import Msg

inherit = "http"
cron = "0 3 * * *"

RE_MAIN_JS = regex(r'"([^"]+/main-es2015\.[^"]+.js)"')
RE_CLIENT_SECRET = regex(r'clientSecret:"([^"]{32})"')
ONE_DAY = timedelta(days=1)

async def fetch(job):
    hotel = job.config["hotel"]
    adults = job.config["adults"]
    start = job.config["start"]
    end = job.config["end"]

    resp = await job.http.get(f"https://onepagebooking.com/{hotel}")
    if resp.status_code != 200:
        raise Exception()

    if (res := RE_MAIN_JS.search(resp.text)) is None:
        raise Exception()

    resp = await job.http.get(f"https://onepagebooking.com{res.group(1)}")
    if resp.status_code != 200:
        raise Exception()

    if (res := RE_CLIENT_SECRET.search(resp.text)) is None:
        raise Exception()

    resp = await job.http.post(
        "https://v5.onepagebooking.com/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "OPB5",
            "client_secret": res.group(1),
            "client_code": hotel,
        },
    )
    if resp.status_code != 200:
        raise Exception()

    token = resp.json()["access_token"]

    resp = await job.http.post(
        "https://v5.onepagebooking.com/api/RatePlan",
        headers = { "Authorization": f"Bearer {token}" },
        json={
            "code": hotel,
            "currencyCode": "EUR",
            "rooms": [{ "RateTypeID": 0, "adults": adults }],
            "nights": (end - start).days,
            "startDate": f"{start:%d.%m.%Y}",
            "endDate": f"{(end - ONE_DAY):%d.%m.%Y}",
            "outputType": 12,
            "clientInfo": {},
        }
    )

    price = round(
        min(
            plan["Price"]
            for plan in resp.json()["RatePlans"]
            if plan["Bookable"]
        ),
        2
    )

    return [ Msg(price, price=price) ]
