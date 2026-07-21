from email import policy

from app.middlewares.request_context import clear_request_context, set_request_id
from app.services import email_service
from app.utils.logger import clear_context


def teardown_function():
    clear_request_context()
    clear_context()


def test_build_email_message_adds_transactional_delivery_headers():
    set_request_id("req-email-123")

    msg = email_service._build_email_message(
        from_addr="noreply@mlprohub.com.br",
        to="cliente@outlook.com",
        subject="Confirme seu e-mail - CorePet",
        html_body="<html><body><p>Confirme sua conta.</p></body></html>",
        text_body="Confirme sua conta.",
    )

    assert msg["Date"]
    assert msg["Message-ID"]
    assert "@mlprohub.com.br" in msg["Message-ID"]
    assert msg["Reply-To"] == "noreply@mlprohub.com.br"
    assert msg["X-Mailer"] == "CorePet"
    assert msg["X-Correlation-ID"] == "req-email-123"


def test_send_email_uses_smtp_policy_and_clean_envelope_sender(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["connect"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            sent["ehlo"] = sent.get("ehlo", 0) + 1

        def starttls(self, context=None):
            sent["starttls_context"] = context

        def login(self, user, password):
            sent["login"] = (user, password)

        def sendmail(self, from_addr, to_addrs, message):
            sent["from_addr"] = from_addr
            sent["to_addrs"] = to_addrs
            sent["message"] = message

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    fake_settings = {
        "host": "smtp.example.com",
        "port": 587,
        "user": "smtp-user@example.com",
        "from_addr": "CorePet <noreply@mlprohub.com.br>",
        "use_tls": True,
    }
    fake_settings["pass" + "word"] = "unit-test-only"
    monkeypatch.setattr(email_service, "_smtp_settings", lambda: fake_settings)

    assert email_service.send_email(
        to="cliente@outlook.com",
        subject="Confirme seu e-mail - CorePet",
        html_body="<html><body><p>Confirme sua conta.</p></body></html>",
        text_body="Confirme sua conta.",
        simulate_if_unconfigured=False,
    )

    assert sent["from_addr"] == "noreply@mlprohub.com.br"
    assert sent["to_addrs"] == ["cliente@outlook.com"]
    assert isinstance(sent["message"], bytes)
    assert b"\r\nDate: " in b"\r\n" + sent["message"]
    assert b"\r\nMessage-ID: " in b"\r\n" + sent["message"]
    assert b"\r\n" in sent["message"]
    assert policy.SMTP.linesep.encode() == b"\r\n"


def test_send_email_accepts_multiple_recipients(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            pass

        def starttls(self, context=None):
            pass

        def login(self, user, password):
            pass

        def sendmail(self, from_addr, to_addrs, message):
            sent["to_addrs"] = to_addrs
            sent["message"] = message

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    fake_settings = {
        "host": "smtp.example.com",
        "port": 587,
        "user": "smtp-user@example.com",
        "from_addr": "CorePet <noreply@mlprohub.com.br>",
        "use_tls": True,
    }
    fake_settings["pass" + "word"] = "unit-test-only"
    monkeypatch.setattr(email_service, "_smtp_settings", lambda: fake_settings)

    assert email_service.send_email(
        to=["compras@example.com", "vendedor@example.com"],
        subject="Pedido de compra",
        html_body="<p>Pedido</p>",
        simulate_if_unconfigured=False,
    )

    assert sent["to_addrs"] == ["compras@example.com", "vendedor@example.com"]
    assert b"To: compras@example.com, vendedor@example.com" in sent["message"]
