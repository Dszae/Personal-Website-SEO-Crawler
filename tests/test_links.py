from crawler.link_extractor import parse_html

def test_html_link_and_alt_extraction():
    data = parse_html(b'<html><head><title>Home</title></head><body><h1>Home</h1><a href="/about">About</a><img src="x.jpg"></body></html>', 'https://example.com/', 'example.com')
    assert data['internal_links'][0]['url'] == 'https://example.com/about'
    assert data['images'][0]['alt'] is None
