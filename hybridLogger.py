import logging
from datetime import datetime
import sys
from pathlib import Path
from contextlib import suppress

class HybridLogger:
    """Context manager for hybrid logging (console + file) with proper resource management"""
    
    def __init__(self, name: str = "app", log_dir: str = "logs"):
        self.name = name
        self.log_dir = log_dir
        self.logger = None
        
    def _setup_logger(self) -> logging.Logger:
        """
        Create and return a logger that both prints to the screen and saves to a file with timestamp.
        
        Returns:
            logging.Logger: a ready to use logger object
        """
        # יצירת תיקיית לוגים אם לא קיימת
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        # שם הקובץ עם תאריך ושעה
        log_filename = Path(self.log_dir) / f"{self.name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

        # פורמט אחיד
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # יצירת לוגר
        logger = logging.getLogger(self.name)
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
        
    def __enter__(self):
        self.logger = self._setup_logger()
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.logger:
            for handler in self.logger.handlers:
                with suppress(OSError, ValueError):
                    handler.flush()
                    handler.close()
            self.logger.handlers.clear()
