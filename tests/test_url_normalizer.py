import pytest
from crawler.url_normalizer import normalize_url

def test_normalize_url_removes_fragment_and_trailing_slash():
    assert normalize_url("https://Example.com/about/?b=2&a=1#section") == "https://example.com/about?a=1&b=2"

def test_rejects_non_http():
    with pytest.raises(ValueError): normalize_url("file:///tmp/x")
