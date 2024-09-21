from babel.dates import format_date, format_time
from babel.numbers import format_currency
from hashlib import blake2b
from jinja2 import Environment, StrictUndefined

env = Environment(
    autoescape=True,
    undefined=StrictUndefined,
)

class Msg:
    def __init__(self, id, **data):
        self.id = id
        self.hash = blake2b(str(id).encode("utf-8")).hexdigest()
        self._data = data

    def __getattr__(self, key):
        return self._data[key]

    def format(self, locale, jobid, action):
        def fdate(dt):
            return format_date(dt, format="full", locale=locale)

        def ftime(dt):
            return format_time(dt, format="short", locale=locale)

        def fdatetime(dt):
            return f"{fdate(dt)} {ftime(dt)}"

        def fprice(num, currency="EUR"):
            return format_currency(num, currency, locale=locale)

        tmpl = env.from_string(action.message_template, globals={
            "jobid": jobid,
            "fdate": fdate,
            "ftime": ftime,
            "fdatetime": fdatetime,
            "fprice": fprice,
        })
        return tmpl.render(**self._data).strip()
