# Imports from project
from src import Logger
from src.constants import config

# Other imports
import uvicorn

if __name__ == '__main__':
    # Logger initialization
    logger = Logger(
        logger_name=config.api_name,
        save_logs=config.save_logs,
        log_max_size_mb=config.log_max_size_mb,
        log_max_backup_count=config.log_max_backup_count,
        logs_dir=config.logs_dir,
        log_filename=config.log_filename
    )

    # Uvicorn config init
    uvicorn_config = {
        'app': 'src:app',
        'host': config.host,
        'port': config.port,
        'log_config': logger.logging_config(),
    }
    # Uvicorn start
    uvicorn.run(**uvicorn_config)
