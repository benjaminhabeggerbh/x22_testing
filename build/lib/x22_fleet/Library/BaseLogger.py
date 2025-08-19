import logging
from logging.handlers import RotatingFileHandler

class BaseLogger:
    def __init__(self, log_to_file=True, log_to_console=False, log_file_path="application.log", max_bytes=250 * 1024 * 1024, backup_count=5):
        self.logger = logging.getLogger("MqttFileTransferLogger")
        self.logger.setLevel(logging.INFO)  # Set logging level to INFO
        self.logger.propagate = False  # Prevent propagation to the root logger

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Add console handler
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Add file handler
        if log_to_file:
            file_handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

if __name__ == "__main__":
    # Initialize the logger with console logging enabled
    logger = BaseLogger(log_to_file=False, log_to_console=True).get_logger()
    
    # Test log messages
    logger.info("This is an INFO level log message.")
    logger.warning("This is a WARNING level log message.")
    logger.error("This is an ERROR level log message.")
    logger.debug("This is a DEBUG level log message (won't show unless level is set to DEBUG).")
