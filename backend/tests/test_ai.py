from app.ai.classifier import ClassificationOutput
from app.ai.response_generator import ResponseOutput
from app.models import MessageType, TicketMessage
from app.services.knowledge_service import ingest_document
from app.ai.embeddings import HashEmbeddingProvider
from tests.conftest import auth_headers, create_ticket

API_KEYS_DOC = """# API Keys, Authentication and Rate Limits

Production keys start with ak_live_ and sandbox keys start with ak_test_.
A sandbox key used against production returns 401 Unauthorized.
"""


def _seed_knowledge(db):
    ingest_document(db, HashEmbeddingProvider(768), "api_keys.md", "text/markdown", API_KEYS_DOC)


def _analyze(client, ticket_id, user):
    response = client.post(f"/api/tickets/{ticket_id}/analyze", headers=auth_headers(user))
    assert response.status_code == 202, response.text
    analysis = client.get(f"/api/tickets/{ticket_id}/ai-analysis", headers=auth_headers(user))
    assert analysis.status_code == 200
    return analysis.json()


def test_analyze_returns_503_when_ollama_unavailable(client, fake_llm, customer, agent):
    fake_llm.available = False
    ticket = create_ticket(client, customer)
    response = client.post(f"/api/tickets/{ticket['id']}/analyze", headers=auth_headers(agent))
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "ollama_unavailable"
    assert "Ollama" in body["detail"]


def test_customers_cannot_use_ai_endpoints(client, customer):
    ticket = create_ticket(client, customer)
    assert client.post(f"/api/tickets/{ticket['id']}/analyze", headers=auth_headers(customer)).status_code == 403
    assert client.get(f"/api/tickets/{ticket['id']}/ai-analysis", headers=auth_headers(customer)).status_code == 403
    assert (
        client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(customer)).status_code
        == 403
    )


def test_full_analysis_creates_pending_draft_without_sending(client, db, customer, agent):
    _seed_knowledge(db)
    ticket = create_ticket(client, customer)
    analysis = _analyze(client, ticket["id"], agent)

    assert analysis["analysis_status"] == "COMPLETED"
    events = [e["event"] for e in analysis["progress"]]
    for expected in (
        "classification_started",
        "classification_completed",
        "priority_completed",
        "retrieval_completed",
        "similar_ticket_search_completed",
        "response_generated",
    ):
        assert expected in events

    draft = analysis["latest_response"]
    assert draft["status"] == "PENDING"
    assert draft["category"] == "API"
    assert draft["priority"] == "HIGH"
    assert draft["knowledge_results"][0]["document_title"] == "API Keys, Authentication and Rate Limits"
    # Invented sources are stripped; real ones are kept.
    assert draft["source_references"] == ["API Keys, Authentication and Rate Limits"]
    assert any("Totally Invented Handbook" in w for w in draft["warnings"])

    # Human-in-the-loop: nothing customer-visible was added by the AI.
    customer_view = client.get(f"/api/tickets/{ticket['id']}", headers=auth_headers(customer)).json()
    assert [m["message_type"] for m in customer_view["messages"]] == ["CUSTOMER"]
    agent_view = client.get(f"/api/tickets/{ticket['id']}", headers=auth_headers(agent)).json()
    assert [m["message_type"] for m in agent_view["messages"]] == ["CUSTOMER", "AI_DRAFT"]
    assert agent_view["category"] == "API" and agent_view["priority"] == "HIGH"
    assert db.query(TicketMessage).filter_by(message_type=MessageType.AGENT).count() == 0


def test_approve_ai_response_posts_message(client, customer, agent):
    ticket = create_ticket(client, customer)
    _analyze(client, ticket["id"], agent)

    response = client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(agent))
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["approver"]["id"] == agent.id

    customer_view = client.get(f"/api/tickets/{ticket['id']}", headers=auth_headers(customer)).json()
    agent_messages = [m for m in customer_view["messages"] if m["message_type"] == "AGENT"]
    assert len(agent_messages) == 1
    assert "ak_live_" in agent_messages[0]["message"]
    assert customer_view["status"] == "WAITING_FOR_CUSTOMER"

    again = client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(agent))
    assert again.status_code == 409


def test_edit_then_approve_marks_edited(client, customer, agent):
    ticket = create_ticket(client, customer)
    _analyze(client, ticket["id"], agent)

    edited = client.patch(
        f"/api/tickets/{ticket['id']}/ai-response",
        json={"edited_response": "Hi Carol, please create a live key (ak_live_)."},
        headers=auth_headers(agent),
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "PENDING"

    approved = client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(agent)).json()
    assert approved["status"] == "EDITED"
    detail = client.get(f"/api/tickets/{ticket['id']}", headers=auth_headers(customer)).json()
    assert detail["messages"][-1]["message"] == "Hi Carol, please create a live key (ak_live_)."


def test_reject_ai_response(client, customer, agent):
    ticket = create_ticket(client, customer)
    _analyze(client, ticket["id"], agent)

    response = client.post(
        f"/api/tickets/{ticket['id']}/ai-response/reject",
        json={"reason": "Not accurate"},
        headers=auth_headers(agent),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["rejection_reason"] == "Not accurate"

    customer_view = client.get(f"/api/tickets/{ticket['id']}", headers=auth_headers(customer)).json()
    assert all(m["message_type"] != "AGENT" for m in customer_view["messages"])

    cannot_approve = client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(agent))
    assert cannot_approve.status_code == 409


def test_regenerate_supersedes_previous_draft(client, customer, agent):
    ticket = create_ticket(client, customer)
    first = _analyze(client, ticket["id"], agent)["latest_response"]

    response = client.post(f"/api/tickets/{ticket['id']}/ai-response/regenerate", headers=auth_headers(agent))
    assert response.status_code == 202
    latest = client.get(f"/api/tickets/{ticket['id']}/ai-analysis", headers=auth_headers(agent)).json()
    assert latest["latest_response"]["id"] != first["id"]
    assert latest["latest_response"]["status"] == "PENDING"

    stats = client.get("/api/analytics/ai", headers=auth_headers(agent)).json()
    assert stats["superseded_count"] == 1
    assert stats["pending_count"] == 1


def test_approve_without_analysis_returns_404(client, customer, agent):
    ticket = create_ticket(client, customer)
    response = client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(agent))
    assert response.status_code == 404


def test_malformed_classification_falls_back(client, fake_llm, customer, agent):
    fake_llm.malformed = {ClassificationOutput}
    ticket = create_ticket(client, customer)
    draft = _analyze(client, ticket["id"], agent)["latest_response"]
    assert draft["category"] == "OTHER"
    assert draft["classification_confidence"] == 0.0
    assert any("malformed" in w.lower() for w in draft["warnings"])


def test_malformed_response_marks_analysis_failed(client, fake_llm, customer, agent):
    fake_llm.malformed = {ResponseOutput}
    ticket = create_ticket(client, customer)
    analysis = _analyze(client, ticket["id"], agent)
    assert analysis["analysis_status"] == "FAILED"
    assert "malformed" in analysis["error"].lower()
    assert analysis["latest_response"] is None


def test_similar_resolved_tickets_are_retrieved(client, customer, other_customer, agent):
    solved = create_ticket(client, other_customer, subject="API returns 401 after key rotation")
    client.post(
        f"/api/tickets/{solved['id']}/resolve",
        json={"resolution_summary": "Customer used sandbox ak_test_ key against production."},
        headers=auth_headers(agent),
    )
    ticket = create_ticket(client, customer)
    draft = _analyze(client, ticket["id"], agent)["latest_response"]
    similar_ids = [t["ticket_id"] for t in draft["similar_tickets"]]
    assert solved["id"] in similar_ids
    assert ticket["id"] not in similar_ids


def test_feedback_and_ai_metrics(client, customer, agent):
    ticket = create_ticket(client, customer)
    _analyze(client, ticket["id"], agent)
    client.post(f"/api/tickets/{ticket['id']}/ai-response/approve", headers=auth_headers(agent))

    feedback = client.post(
        f"/api/tickets/{ticket['id']}/ai-feedback",
        json={"rating": 4, "comments": "Good draft"},
        headers=auth_headers(agent),
    )
    assert feedback.status_code == 201
    assert feedback.json()["rating"] == 4

    invalid = client.post(
        f"/api/tickets/{ticket['id']}/ai-feedback", json={"rating": 9}, headers=auth_headers(agent)
    )
    assert invalid.status_code == 422

    stats = client.get("/api/analytics/ai", headers=auth_headers(agent)).json()
    assert stats["approved_count"] == 1
    assert stats["approval_rate"] == 1.0
    assert stats["average_feedback_rating"] == 4.0


def test_auto_analysis_failure_does_not_block_ticket_creation(client, fake_llm, customer, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "AI_AUTO_ANALYZE", True)
    fake_llm.available = False
    ticket = create_ticket(client, customer)
    assert ticket["ai_analysis_status"] == "FAILED"
    assert ticket["ai_error"] is None  # internal error details are hidden from customers
