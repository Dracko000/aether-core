from aether.config import Settings
def test_config_defaults():
    settings = Settings()
    assert settings.API_PORT == 8456
