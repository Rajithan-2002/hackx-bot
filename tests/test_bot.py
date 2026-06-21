import pytest
from unittest.mock import MagicMock, patch
from app.services.domain_guard import is_domain_valid
from app.services.rag import resolve_aliases, answer_question


def test_domain_guard():
    assert is_domain_valid("When is the registration deadline?") is True
    assert is_domain_valid("What is the weather like today?") is False


def test_resolve_aliases():
    assert resolve_aliases("group size") == "team size"
    assert (
        resolve_aliases("when is the closing date?")
        == "when is the registration deadline?"
    )


@pytest.mark.asyncio
@patch("app.services.rag.supabase")
@patch("app.services.rag.get_embedding")
async def test_domain_guard_rejection(mock_embed, mock_supabase):
    mock_embed.return_value = [0.1] * 1536
    res = await answer_question("What is the capital of France?")
    assert res["tier"] == 1
    assert res["source"] == "domain_guard"
    assert "Sorry, I can only help" in res["answer"]


@pytest.mark.asyncio
@patch("app.services.rag.supabase")
@patch("app.services.rag.get_cached_response")
async def test_cache_hit(mock_get_cache, mock_supabase):
    mock_get_cache.return_value = "This is a cached answer."
    res = await answer_question("When does registration open?")
    assert res["tier"] == 2
    assert res["source"] == "cache"
    assert res["answer"] == "This is a cached answer."


@pytest.mark.asyncio
@patch("app.services.rag.supabase")
@patch("app.services.rag.get_cached_response")
async def test_exact_faq_match(mock_get_cache, mock_supabase):
    mock_get_cache.return_value = None
    mock_faq_table = MagicMock()
    mock_supabase.table.return_value = mock_faq_table

    mock_faq_table.select.return_value.execute.return_value = MagicMock(
        data=[
            {
                "question": "What is the team size?",
                "answer": "Teams must consist of 2 to 4 members.",
                "aliases": ["team limit", "max members"],
            }
        ]
    )

    res = await answer_question("What is the team size?")
    assert res["tier"] == 4
    assert res["source"] == "faq_exact"
    assert res["answer"] == "Teams must consist of 2 to 4 members."


@pytest.mark.asyncio
@patch("app.services.rag.supabase")
@patch("app.services.rag.get_cached_response")
@patch("app.services.rag.get_embedding")
async def test_vector_match_high_confidence(mock_embed, mock_get_cache, mock_supabase):
    mock_get_cache.return_value = None
    mock_faq_table = MagicMock()
    mock_faq_table.select.return_value.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = mock_faq_table

    mock_embed.return_value = [0.1] * 1536

    mock_supabase.rpc.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "123",
                "chunk_text": "The main event venue is Royal College MAS Arena.",
                "metadata": {"source": "HackX Rulebook", "section": "Venue"},
                "similarity": 0.97,
            }
        ]
    )

    res = await answer_question("Where is the venue?")
    assert res["tier"] == 5
    assert res["source"] == "HackX Rulebook"
    assert "MAS Arena" in res["answer"]


@pytest.mark.asyncio
@patch("app.services.rag.supabase")
@patch("app.services.rag.get_cached_response")
@patch("app.services.rag.get_embedding")
@patch("app.services.rag.generate_response")
async def test_llm_fallback(mock_llm, mock_embed, mock_get_cache, mock_supabase):
    mock_get_cache.return_value = None
    mock_faq_table = MagicMock()
    mock_faq_table.select.return_value.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = mock_faq_table

    mock_embed.return_value = [0.1] * 1536

    mock_supabase.rpc.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "123",
                "chunk_text": "First-year students are eligible.",
                "metadata": {"source": "HackX Rulebook", "section": "Eligibility"},
                "similarity": 0.35,
            }
        ]
    )

    mock_llm.return_value = "Yes, first-year university students are eligible to join."

    res = await answer_question("Can freshman participate?")
    assert res["tier"] == 6
    assert res["source"] == "llm_generated"
    assert res["answer"] == "Yes, first-year university students are eligible to join."


@pytest.mark.asyncio
@patch("app.services.rag.supabase")
@patch("app.services.rag.get_cached_response")
@patch("app.services.rag.get_embedding")
@patch("app.services.rag.generate_response")
async def test_llm_fallback_failure_retrieval_only(
    mock_llm, mock_embed, mock_get_cache, mock_supabase
):
    mock_get_cache.return_value = None
    mock_faq_table = MagicMock()
    mock_faq_table.select.return_value.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = mock_faq_table

    mock_embed.return_value = [0.1] * 1536
    mock_supabase.rpc.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "123",
                "chunk_text": "Teams must have 2 to 4 members.",
                "metadata": {"source": "Rules Doc", "section": "Team size"},
                "similarity": 0.35,
            }
        ]
    )

    mock_llm.side_effect = Exception("OpenAI rate limit hit")

    res = await answer_question("How many members in a team?")
    assert res["tier"] == 6
    assert res["source"] == "retrieved_chunks"
    assert "I found the following relevant information" in res["answer"]
    assert "Teams must have 2 to 4 members." in res["answer"]


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
            "tier": 2,
        }

        # Make 30 requests - they should all succeed (200 OK)
        for _ in range(30):
            response = client.post(
                "/api/chat", json={"message": "hello", "session_id": "test"}
            )
            assert response.status_code == 200

        # The 31st request should be rate limited (429 Too Many Requests)
        response = client.post(
            "/api/chat", json={"message": "hello", "session_id": "test"}
        )
        assert response.status_code == 429
