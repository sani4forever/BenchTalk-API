"""
This module contains the base implementation of a configurator for this
project. It loads every possible environment variable.
"""

import os

from dotenv import load_dotenv

__all__ = ['MainConfigurator']


class MainConfigurator:
    def __init__(self, env_path='.env'):
        """
        Loads configuration from environment variables or defaults.
        """
        self._env_path = env_path
        self.cfg = {}
        dev = bool(int(os.getenv('START_DEV', '0')))
        if dev:
            self._env_path = '.env.dev'
        self.load_env(self._env_path)

    def __repr__(self):
        return f'MainConfigurator(env_path={self._env_path})'

    def load_env(self, env_path: str):
        self._env_path = env_path
        load_dotenv(self._env_path)
        self.cfg = {
            'dev': bool(int(os.getenv('START_DEV', '0'))),
            'host': os.getenv('HOST', '0.0.0.0'),
            'port': int(os.getenv('PORT', '8000')),
            'save_logs': bool(int(os.getenv('SAVE_LOGS', '1'))),
            'log_max_size_mb': int(os.getenv('LOG_MAX_SIZE_MB', '5')),
            'log_max_backup_count':
                int(os.getenv('LOG_MAX_BACKUP_COUNT', '5')),
            'logs_dir': os.getenv('LOGS_DIR', 'logs'),
            'log_filename': os.getenv('LOG_FILENAME'),
            'api_name': os.getenv('API_NAME', 'Main'),
            'main_api_address': os.getenv('MAIN_API_ADDRESS', '/api'),
            'main_site': os.getenv('MAIN_SITE'),
            'static_dir': os.getenv('STATIC_DIR', 'static'),
            'favicon': os.path.join(
                os.getenv('STATIC_DIR', 'static'),
                os.getenv('FAVICON', 'favicon.ico')
            ),
            'redoc_js': os.path.join(
                os.getenv('STATIC_DIR', 'static'),
                os.getenv('REDOC_JS', 'redoc.standalone.js')
            ),
            'swagger_js': os.path.join(
                os.getenv('STATIC_DIR', 'static'),
                os.getenv('SWAGGER_JS', 'swagger-ui-bundle.js')
            ),
            'swagger_css': os.path.join(
                os.getenv('STATIC_DIR', 'static'),
                os.getenv('SWAGGER_CSS', 'swagger-ui.css')
            ),
            'postgres_host': os.getenv('POSTGRES_HOST', 'localhost'),
            'postgres_port': int(os.getenv('POSTGRES_PORT', '5432')),
            'postgres_user': os.getenv('POSTGRES_USER', 'postgres'),
            'postgres_password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
            'postgres_name': os.getenv('POSTGRES_NAME', 'postgres'),
        }
        if not self.cfg['main_api_address'].startswith('/'):
            self.cfg['main_api_address'] = f'/{self.cfg["main_api_address"]}'
        self.cfg['main_site'] = (
            f'\n\nMain address: {self.cfg["main_site"]}'
            if self.cfg['main_site'] else ''
        )

    def get_config(self):
        return self.cfg

    def set_config(self, config):
        self.cfg = config

    @property
    def config(self):
        return self.cfg

    @config.setter
    def config(self, config):
        self.cfg = config

    @property
    def env_path(self):
        return self.env_path

    @env_path.setter
    def env_path(self, env_path: str):
        self._env_path = env_path
        self.load_env(self._env_path)

    @property
    def dev(self):
        return self.config['dev']

    @property
    def host(self):
        return self.config['host']

    @property
    def port(self):
        return self.config['port']

    @property
    def save_logs(self):
        return self.config['save_logs']

    @property
    def log_max_size_mb(self):
        return self.config['log_max_size_mb']

    @property
    def log_max_backup_count(self):
        return self.config['log_max_backup_count']

    @property
    def logs_dir(self):
        return self.config['logs_dir']

    @property
    def log_filename(self):
        return self.config['log_filename']

    @property
    def api_name(self):
        return self.config['api_name']

    @property
    def main_api_address(self):
        return self.config['main_api_address']

    @property
    def main_site(self):
        return self.config['main_site']

    @property
    def static_dir(self):
        return self.config['static_dir']

    @property
    def favicon(self):
        return self.config['favicon']

    @property
    def redoc_js(self):
        return self.config['redoc_js']

    @property
    def swagger_js(self):
        return self.config['swagger_js']

    @property
    def swagger_css(self):
        return self.config['swagger_css']

    @property
    def postgres_host(self):
        return self.config['postgres_host']

    @property
    def postgres_port(self):
        return self.config['postgres_port']

    @property
    def postgres_user(self):
        return self.config['postgres_user']

    @property
    def postgres_password(self):
        return self.config['postgres_password']

    @property
    def postgres_name(self):
        return self.config['postgres_name']
