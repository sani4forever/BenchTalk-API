"""
Base constants for all API version.
"""

from .configurator import MainConfigurator

__all__ = [
    'API_NAME',
    'MAIN_API_ADDRESS',
    'MAIN_SITE',
    'POSTGRES_HOST',
    'POSTGRES_NAME',
    'POSTGRES_PASSWORD',
    'POSTGRES_PORT',
    'POSTGRES_USER',
]

config = MainConfigurator()

API_NAME = config.api_name
MAIN_API_ADDRESS = config.main_api_address
MAIN_SITE = config.main_site

POSTGRES_HOST = config.postgres_host
POSTGRES_NAME = config.postgres_name
POSTGRES_PASSWORD = config.postgres_password
POSTGRES_PORT = config.postgres_port
POSTGRES_USER = config.postgres_user
