from app.bling_oauth_routes import _html_erro


def test_html_erro_escapes_message_content():
    html = _html_erro('<script>alert("x")</script>')

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&quot;x&quot;" in html
