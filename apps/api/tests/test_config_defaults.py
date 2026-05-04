from app.config import Settings


def test_allow_dev_wipe_endpoints_default_false() -> None:
    settings = Settings(_env_file=None)
    assert settings.allow_dev_wipe_endpoints is False
