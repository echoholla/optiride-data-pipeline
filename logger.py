import logging


def get_logger(name):
    Logger = logging.getLogger(name)
    Logger.setLevel(logging.INFO)
    
    if not Logger.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s -%(levelname)s -%(message)s"
        )
        ch.setFormatter(formatter)
        Logger.addHandler(ch)
        
    return Logger
        