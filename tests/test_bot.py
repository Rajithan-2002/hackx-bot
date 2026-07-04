import pytest
from unittest.mock import MagicMock, patch
from app.services.rag import answer_question

@pytest.mark.asyncio
@patch("app.services.rag.get_cached_response")
async def test_greeting_response(mock_get_cache):
    res = await answer_question("hi", "hackx")
    assert res["tier"] == 0
    assert res["source"] == "greeting"
    assert "HackX Assistant" in res["answer"]

    res_jr = await answer_question("hello", "hackxjr")
    assert res_jr["tier"] == 0
    assert res_jr["source"] == "greeting"
    assert "HackX Jr Assistant" in res_jr["answer"]


@pytest.mark.asyncio
@patch("app.services.rag.get_cached_response")
async def test_cache_hit(mock_get_cache):
    mock_get_cache.return_value = "This is a cached answer."
    res = await answer_question("When does registration open?", "hackx")
    assert res["tier"] == 1
    assert res["source"] == "cache"
    assert res["answer"] == "This is a cached answer."


@pytest.mark.asyncio
@patch("app.services.rag.get_cached_response")
@patch("app.services.rag.generate_response")
async def test_llm_synthesis(mock_llm, mock_get_cache):
    mock_get_cache.return_value = None
    mock_llm.return_value = "Registration opens on 4th July 2026."

    res = await answer_question("When does registration open?", "hackx")
    assert res["tier"] == 2
    assert res["source"] == "llm_generated"
    assert res["answer"] == "Registration opens on 4th July 2026."


def test_app_import():
    from fastapi import FastAPI
    from app.main import app as fastapi_app

    assert isinstance(fastapi_app, FastAPI)


def test_rate_limiter_integration():
    from fastapi.testclient import TestClient
    from app.main import app

    # Reset limiter state before the test to avoid interference from other tests/runs
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()

    client = TestClient(app)

    with patch("app.main.answer_question") as mock_answer:
        mock_answer.return_value = {
            "answer": "Test answer",
            "source": "cache",
            "tier": 1,
        }

        # Make 30 requests - they should all succeed (200 OK)
        for _ in range(30):
            response = client.post(
                "/api/chat", json={"message": "hello", "competition_id": "hackx", "session_id": "test"}
            )
            assert response.status_code == 200

        # The 31st request should be rate limited (429 Too Many Requests)
        response = client.post(
            "/api/chat", json={"message": "hello", "competition_id": "hackx", "session_id": "test"}
        )
        assert response.status_code == 429
