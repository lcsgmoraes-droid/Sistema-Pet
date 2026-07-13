from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middlewares.security_headers import SecurityHeadersMiddleware


def _client(base_url: str = "https://testserver") -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    def index():
        return {"status": "ok"}

    return TestClient(app, base_url=base_url)


def test_security_headers_are_consistent_on_https_response():
    response = _client().get("/")

    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-xss-protection"] == "0"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=(self), payment=(self)"
    )
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "object-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"].startswith("max-age=")


def test_untrusted_forwarded_proto_does_not_enable_hsts_on_http():
    response = _client(base_url="http://testserver").get(
        "/", headers={"X-Forwarded-Proto": "https"}
    )

    assert "strict-transport-security" not in response.headers
