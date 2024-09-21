from collections.abc import Mapping
from logging import getLogger
from pathlib import Path
from tomllib import load as decode_toml, TOMLDecodeError

logger = getLogger("polligram")

class Config(Mapping):
    def __init__(self):
        self._data = None
        self.path = Path(f"{__package__}.toml").resolve()
        self.reload()

    def reload(self):
        with open(self.path, "rb") as fp:
            try:
                self._data = decode_toml(fp)
            except TOMLDecodeError:
                if self._data is None:
                    raise
                logger.warning(
                    "Couldn't reload configuration file.",
                    exc_info=True,
                )

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)
