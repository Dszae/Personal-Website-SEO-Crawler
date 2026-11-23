from crawler.link_extractor import parse_html

def test_html_link_and_alt_extraction():
    data = parse_html(b'<html><head><title>Home</title></head><body><h1>Home</h1><a href="/about">About</a><img src="x.jpg"></body></html>', 'https://example.com/', 'example.com')
    assert data['internal_links'][0]['url'] == 'https://example.com/about'
    assert data['images'][0]['alt'] is None

def test_links_are_classified_by_host_not_port_or_userinfo():
    html = (
        b'<a href="/about">About</a>'
        b'<a href="https://example.com:8443/blog">Blog</a>'
        b'<a href="https://Example.COM/contact">Contact</a>'
        b'<a href="https://user@example.com/login">Login</a>'
        b'<a href="https://example.com./docs">Docs</a>'
        b'<a href="https://other.org/">Other</a>'
        b'<a href="https://example.com.evil.net/">Lookalike</a>'
    )
    # A site served on a non-default port: every resolved URL carries ":8443".
    data = parse_html(html, 'https://example.com:8443/', 'example.com')
    assert [link['anchor'] for link in data['internal_links']] == ['About', 'Blog', 'Contact', 'Login', 'Docs']
    assert [link['anchor'] for link in data['external_links']] == ['Other', 'Lookalike']
