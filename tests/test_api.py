from fastapi.testclient import TestClient

from src import app
from src.configurator import MainConfigurator

config = MainConfigurator()
base_address = config.main_api_address
api_version = '/v1'

client = TestClient(app)


def test_root():
    response = client.get(f'{base_address}/')
    assert response.status_code == 200
    assert 'welcome_text' in response.json()


def test_docs_redirect():
    response = client.get(
        f'{base_address}{api_version}/docs', follow_redirects=False
    )
    assert response.status_code == 301
    assert 'location' in response.headers


def test_redoc_redirect():
    response = client.get(
        f'{base_address}{api_version}/redoc', follow_redirects=False
    )
    assert response.status_code == 301
    assert 'location' in response.headers


def test_openapi_json_redirect():
    response = client.get(
        f'{base_address}{api_version}/openapi.json', follow_redirects=False
    )
    assert response.status_code == 301
    assert 'location' in response.headers
