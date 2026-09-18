from app.config import get_settings


def test_settings_loads() -> None:
    settings = get_settings()
    assert settings.app_name == 'the-textile-care-api'
    assert settings.app_env in {'development', 'test', 'staging', 'production'}
