from polligram import *

inherit = "html"
cron = "0 * * * *"
url = "https://www.groupon.de/partial/browse/get-paginated-cards"
message = '''
<a href="{{ href }}">{{ jobid }} für {{ fprice(price) }}</a>
'''

def decode(resp):
    return resp.json()["cardsHtml"]

async def request_kwargs(job):
    query = job.config["query"]
    latitude = job.config["latitude"]
    longitude = job.config["longitude"]
    distance = job.config.get("distance", "0.5")
    return dict(
        params={
            "query": query,
            "distance": f"[0.0..{distance}]",
        },
        cookies={
            "ell": f"{latitude},{longitude}",
            "user_locale": "de_DE",
        },
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) "
                "Gecko/20100101 Firefox/129.0"
            ),
        },
    )

async def action(job, soup):
    if not (el := soup.find("figure")):
        return []

    href = el.find("a")["href"]
    price = el.find(class_="cui-purple-price")
    if not price:
        price = el.find(class_="cui-price-discount")
    price = float(
        price.text.replace("Ab", "")
                  .replace("€", "")
                  .replace(",", ".")
                  .strip()
    )

    return [
        Msg(
            f"{el['data-bhc']}{price}",
            href=href,
            price=price,
        )
    ]
