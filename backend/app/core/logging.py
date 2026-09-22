import logging

from app.core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # SQL visible solo en desarrollo. Se hace con el nivel del logger y no con
    # create_engine(echo=True), que añade un handler propio y duplica cada línea
    # (la suya y la del handler raíz de basicConfig).
    if settings.env == "development":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
