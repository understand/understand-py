import uuid


class TokenProvider:
    def __init__(self) -> None:
        self._token = ""
        self.generate()

    def get_token(self) -> str:
        return self._token

    def generate(self) -> str:
        self._token = str(uuid.uuid4())
        return self._token

