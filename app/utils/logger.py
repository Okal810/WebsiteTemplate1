import logging
import logging.handlers
import os
import sys

# Try to import colorlog for colored console output, fallback to standard logging if not available
try:
    import colorlog
    HAVE_COLORLOG = True
except ImportError:
    HAVE_COLORLOG = False

def setup_logger(app):
    """
    Configures the application logger with rotating file handler and console handler.
    """
    
    # 1. Create logs directory if it doesn't exist
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    log_dir = os.path.join(base_dir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, 'server.log')

    # 2. Define Formatters
    file_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if HAVE_COLORLOG:
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        console_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
            datefmt='%H:%M:%S'
        )

    # 3. Setup File Handler (Rotating)
    # Max size 10MB, keep last 5 logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # 4. Setup Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG) # Show debug logs in console

    # 5. Attach specific loggers or root logger
    # We want to catch Flask's logs and our own app logs
    root_log = logging.getLogger()
    root_log.setLevel(logging.DEBUG)
    
    # Remove default handlers to avoid duplicates if re-initialized
    if root_log.hasHandlers():
        root_log.handlers.clear()

    root_log.addHandler(file_handler)
    root_log.addHandler(console_handler)

    # Also ensure the app logger uses these handlers (Flask's internal logger)
    app.logger.handlers = []
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    app.logger.info("Logger initialized successfully.")
    app.logger.info(f"Log file: {log_file_path}")
