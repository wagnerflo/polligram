from collections.abc import Mapping
from pathlib import Path
from tomllib import load as decode_toml

class Config(Mapping):
    def __init__(self):
        self.path = Path(f"{__package__}.toml").resolve()
        self.reload()

    def reload(self):
        with open(self.path, "rb") as fp:
            self._data = decode_toml(fp)

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)
