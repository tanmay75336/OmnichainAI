import logging


def configure_logging(app):
    log_level = logging.DEBUG if app.config["DEBUG"] else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False
