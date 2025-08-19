import logging
from logging.handlers import RotatingFileHandler
import inspect

class BaseLogger:
    def __init__(self, log_to_file=True, log_to_console=False, log_file_path="application.log", max_bytes=250 * 1024 * 1024, backup_count=5):
        # Automatically determine the owning class name
        frame = inspect.currentframe().f_back
        owner_class_name = frame.f_locals.get('self', None)
        if owner_class_name:
            owner_class_name = owner_class_name.__class__.__name__
        else:
            owner_class_name = "UnknownClass"

        self.logger = logging.getLogger(owner_class_name)
        self.logger.setLevel(logging.INFO)  # Set logging level to INFO
        self.logger.propagate = False  # Prevent propagation to the root logger

        # Standard formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(pathname)s:%(lineno)d)')

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
    class ExampleClass:
        def __init__(self):
            self.logger = BaseLogger(log_to_file=False, log_to_console=True).get_logger()

        def example_method(self):
            self.logger.info("This is an INFO level log message.")
            self.logger.error("This is an ERROR level log message.")

    example = ExampleClass()
    example.example_method()
