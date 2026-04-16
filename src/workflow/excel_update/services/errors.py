class ExcelUpdateError(Exception):
    def __init__(
        self,
        *,
        code: int,
        http_status: int,
        message: str,
        error: dict | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.error = error
