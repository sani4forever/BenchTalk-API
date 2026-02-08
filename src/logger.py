"""
This module contains the base implementation of a logger and special method
in ``Logger`` class for creating configuration for uvicorn.
"""
import logging
import os
from datetime import datetime

__all__ = ['Logger']

DEFAULT_LOG_DIR = 'logs'
DEFAULT_LOG_NAME = datetime.now().strftime('%Y-%m-%d__%H-%M-%S%z') + '.log'
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H-%M-%S%z'


class Logger:
    def __init__(
            self,
            logger_name: str = 'logger',
            save_logs: bool = True,
            log_max_size_mb: int = 5,
            log_max_backup_count: int = 5,
            logs_dir: str = DEFAULT_LOG_DIR,
            log_filename: str = DEFAULT_LOG_NAME
    ):
        """
        Initializes logging for console and for file output
        if ``save_logs`` is True.
        """
        self._logger_name = logger_name if logger_name else 'logger'
        self._save_logs = save_logs if save_logs else True
        self._logs_dir = logs_dir if logs_dir else DEFAULT_LOG_DIR
        self._log_filename = log_filename if log_filename else DEFAULT_LOG_NAME
        log_max_size_mb = log_max_size_mb if log_max_size_mb else 5
        log_max_backup_count = (
            log_max_backup_count if log_max_backup_count else 5
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT
        )
        stream_handler.setFormatter(formatter)

        self._logger = logging.getLogger(self._logger_name)
        self._logger.setLevel(logging.INFO)
        self._logger.addHandler(stream_handler)
        if self._save_logs:
            os.makedirs(self._logs_dir, exist_ok=True)
            full_log_path = os.path.join(self._logs_dir, self._log_filename)
            file_handler = logging.handlers.RotatingFileHandler(
                full_log_path,
                maxBytes=log_max_size_mb * 1024 * 1024,
                backupCount=log_max_backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    @property
    def logger(self):
        return self._logger

    def get_logger(self):
        return self._logger

    def logging_config(self) -> dict:
        """Creating configuration for uvicorn logging."""
        cfg = {
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'default': {
                    'format': DEFAULT_FORMAT,
                    'datefmt': DEFAULT_DATE_FORMAT
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'default',
                }
            },
            'loggers': {
                'uvicorn': {
                    'handlers': ['console'],
                    'level': 'TRACE',
                    'propagate': False,
                },
                'uvicorn.access': {
                    'handlers': ['console'],
                    'level': 'TRACE',
                    'propagate': False,
                },
                'uvicorn.error': {
                    'handlers': ['console'],
                    'level': 'TRACE',
                    'propagate': False,
                },
                'uvicorn.asgi': {
                    'handlers': ['console'],
                    'level': 'TRACE',
                    'propagate': False,
                },
                self._logger_name: {
                    'handlers': ['console'],
                    'level': 'TRACE',
                    'propagate': False,
                },
            }
        }
        if self._save_logs:
            cfg['handlers']['file'] = {
                'class': 'logging.FileHandler',
                'level': 'INFO',
                'formatter': 'default',
                'filename': os.path.join(
                    self._logs_dir, self._log_filename
                )
            }
            logger_names = (
                'uvicorn',
                'uvicorn.access',
                'uvicorn.error',
                'uvicorn.asgi',
                self._logger_name,
            )
            for logger_name in logger_names:
                cfg['loggers'][logger_name]['handlers'].append('file')
        return cfg
