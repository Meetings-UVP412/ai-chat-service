import signal
import logging

logger = logging.getLogger(__name__)
shutdown_flag = False


def set_shutdown_flag(signum, frame):
    global shutdown_flag
    logger.info(f"Получен сигнал завершения {signum}")
    shutdown_flag = True


def get_shutdown_flag():
    global shutdown_flag
    return shutdown_flag


def setup_signal_handlers():
    signal.signal(signal.SIGINT, set_shutdown_flag)
    signal.signal(signal.SIGTERM, set_shutdown_flag)
