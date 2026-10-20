import logging
from loguru import logger


class PropogateHandler(logging.Handler):
    def emit(self, record) -> None:
        logging.getLogger(record.name).handle(record)


logger.add(PropogateHandler(), format="{time:YYYY-MM-DD at HH:mm:ss} | {message}")


