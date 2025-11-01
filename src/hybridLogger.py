import logging
from datetime import datetime
import sys
import traceback
from pathlib import Path
from contextlib import suppress
from typing import Optional, Dict

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for stdout and brackets format"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = False):
        self.use_colors = use_colors
        # Format: [time] [level] [class] message
        super().__init__('[%(asctime)s] [%(levelname)s] [%(class_name)s] %(message)s')
    
    def format(self, record: logging.LogRecord) -> str:
        # Add class_name if not present
        if not hasattr(record, 'class_name'):
            record.class_name = 'Main'
            
        formatted = super().format(record)
        
        # Add colors for stdout only
        if self.use_colors:
            level_name = record.levelname
            color = self.COLORS.get(level_name, self.COLORS['RESET'])
            formatted = f"{color}{formatted}{self.COLORS['RESET']}"
        
        return formatted

class ClassLogger:
    """Per-class logger wrapper with level filtering"""
    
    def __init__(self, main_logger: logging.Logger, class_name: str, level: int):
        self.main_logger = main_logger
        self.class_name = class_name
        self.level = level
    
    def _log(self, level: int, message: str, exc_info: bool = False) -> None:
        """Internal logging method"""
        if level >= self.level:
            # Create log record with class name  
            import sys
            exc_info_tuple = sys.exc_info() if exc_info else None
            record = self.main_logger.makeRecord(
                self.main_logger.name, level, "", 0, message, (), exc_info_tuple
            )
            record.class_name = self.class_name
            self.main_logger.handle(record)
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        self._log(logging.DEBUG, message)
    
    def info(self, message: str) -> None:
        """Log info message"""
        self._log(logging.INFO, message)
    
    def warning(self, message: str) -> None:
        """Log warning message"""
        self._log(logging.WARNING, message)
    
    def error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Log error message with optional exception details"""
        if exception:
            # Automatically extract exception details
            exc_type = type(exception).__name__
            tb = traceback.extract_tb(exception.__traceback__)
            filename, lineno, func, text = tb[-1] if tb else ("unknown", 0, "unknown", "")
            enhanced_message = f"{message} | Type: {exc_type} | File: {filename} | Line: {lineno}"
            self._log(logging.ERROR, enhanced_message, exc_info=True)
        else:
            self._log(logging.ERROR, message)
    
    def critical(self, message: str) -> None:
        """Log critical message"""
        self._log(logging.CRITICAL, message)

class HybridLogger:
    """Enhanced logger factory with per-class logging and colored output"""
    
    def __init__(self, name: str = "app", log_dir: str = "logs"):
        self.name = name
        self.log_dir = log_dir
        self.main_logger: Optional[logging.Logger] = None
        self.class_loggers: Dict[str, ClassLogger] = {}
        self._setup_main_logger()
        
    def _setup_main_logger(self) -> None:
        """Create main logger with file and console handlers"""
        # Create log directory
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate log filename with timestamp
        log_filename = Path(self.log_dir) / f"{self.name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        
        # Create main logger
        self.main_logger = logging.getLogger(self.name)
        self.main_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.main_logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(use_colors=True)
        console_handler.setFormatter(console_formatter)
        self.main_logger.addHandler(console_handler)
        
        # File handler without colors
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_formatter = ColoredFormatter(use_colors=False)
        file_handler.setFormatter(file_formatter)
        self.main_logger.addHandler(file_handler)
    
    def get_class_logger(self, class_name: str, level: int = logging.INFO) -> ClassLogger:
        """
        Get a logger for a specific class with custom log level
        
        Args:
            class_name: Name of the class for log identification
            level: Minimum log level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            ClassLogger: Logger instance for the specified class
        """
        if class_name not in self.class_loggers:
            self.class_loggers[class_name] = ClassLogger(
                self.main_logger, class_name, level
            )
        return self.class_loggers[class_name]
    
    def get_main_logger(self, level: int = logging.INFO) -> ClassLogger:
        """
        Get the main application logger (convenience method)
        
        Args:
            level: Minimum log level for main logger
            
        Returns:
            ClassLogger: Main logger instance with class_name="Main"
        """
        return self.get_class_logger("Main", level)
    
    def cleanup(self) -> None:
        """Clean up logger resources"""
        if self.main_logger:
            for handler in self.main_logger.handlers:
                with suppress(OSError, ValueError):
                    handler.flush()
                    handler.close()
            self.main_logger.handlers.clear()
