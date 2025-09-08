from app.core.pagination import try_decode_cursor


def test_try_decode_cursor_handles_none_and_bad():
    assert try_decode_cursor(None) is None
    assert try_decode_cursor("") is None
    assert try_decode_cursor("not-base64") is None
