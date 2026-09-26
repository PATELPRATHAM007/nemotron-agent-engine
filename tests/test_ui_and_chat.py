from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ui_endpoints():
    # Test /ui
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "NVIDIA Nemotron 3 Ultra" in resp.text
    assert "Autonomous Mission" in resp.text
    assert "Direct Chat" in resp.text

    # Test /chat alias
    resp_chat = client.get("/chat")
    assert resp_chat.status_code == 200
    assert "text/html" in resp_chat.headers.get("content-type", "")
    assert "Nemotron 3 Ultra" in resp_chat.text


def test_chat_stream_endpoint():
    payload = {
        "messages": [{"role": "user", "content": "Ping test"}],
        "temperature": 0.6,
        "enable_thinking": True,
    }
    resp = client.post("/api/v1/agent/chat/stream", json=payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    # Check that streamed response contains data
    content = resp.text
    assert len(content) > 0


def test_favicon_endpoint():
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert "image/svg+xml" in resp.headers.get("content-type", "")
    assert "⚡" in resp.text

