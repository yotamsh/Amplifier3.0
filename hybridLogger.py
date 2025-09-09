import logging
from datetime import datetime
import sys
from pathlib import Path

def setup_logger(name: str = "app", log_dir: str = "logs") -> logging.Logger:
    """
    create and return a logger that both prints to the screen and saves to a file with timestamp.

    Args:
        name (str): name of the logger.
        log_dir (str): directory to save the logs.

    Returns:
        logging.Logger: a ready to use logger object
    """
    # יצירת תיקיית לוגים אם לא קיימת
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # שם הקובץ עם תאריך ושעה
    log_filename = Path(log_dir) / f"{name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    # פורמט אחיד
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # יצירת לוגר
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # מניעת כפילות אם הפונקציה נקראת פעמיים
    if not logger.handlers:
        # למסך (stdout → יתפס גם ע"י systemd/journalctl)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # לקובץ
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
