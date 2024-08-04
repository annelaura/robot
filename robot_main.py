# robot_main.py
import RPi.GPIO as GPIO
from robot_functions import control_doors
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, MAX_LOG_FILE_SIZE, BACKUP_COUNT

gpio_setup_done = False

def setup_logging():
    # Configure logging with rotation based on file size
    log_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_FILE_SIZE,
        backupCount=BACKUP_COUNT
    )
    log_handler.setLevel(logging.INFO)
    log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)

def cleanup_gpio():
    if gpio_setup_done:
        GPIO.cleanup()

if __name__ == "__main__":
    setup_logging()
    logging.info('Robot main started')
    try:
        control_doors()
    except KeyboardInterrupt:
        logging.info("Program interrupted and stopped by user.")
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
    finally:
        cleanup_gpio()
        logging.info('Robot main ended')
