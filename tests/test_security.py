import pytest
from crawler.security import validate_public_url

def test_rejects_private_and_unconfigured_hosts():
    with pytest.raises(ValueError): validate_public_url("http://localhost/", {"localhost"})
    with pytest.raises(ValueError): validate_public_url("https://example.com/", {"www.dipeshsapkota7.com.np"})
