class Request:
    """Сущность сетевого запроса / заявки."""

    def __init__(self, source_id: int, req_number: int, gen_time: float):
        self.source_id = source_id
        self.req_number = req_number
        self.gen_time = gen_time

    def __repr__(self):
        return f"И{self.source_id}.{self.req_number}"
