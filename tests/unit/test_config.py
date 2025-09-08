from app.core.config import Settings


def test_cors_split_string_to_list():
    s = Settings(CORS_ORIGINS="http://a,http://b")
    assert s.CORS_ORIGINS == ["http://a", "http://b"]
