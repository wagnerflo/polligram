from hashlib import blake2b

class Msg:
    def __init__(self, id, **data):
        self.id = id
        self.hash = blake2b(str(id).encode("utf-8")).hexdigest()
        self.data = data
