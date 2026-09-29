from app.models import TicketEmbedding
from tests.conftest import auth_headers, create_ticket


def test_customer_creates_ticket(client, customer):
    ticket = create_ticket(client, customer)
    assert ticket["status"] == "OPEN"
    assert ticket["customer"]["id"] == customer.id
    assert ticket["messages"][0]["message_type"] == "CUSTOMER"
    assert ticket["category"] is None


def test_ticket_creation_validates_input(client, customer):
    response = client.post(
        "/api/tickets", json={"subject": "x", "description": "short"}, headers=auth_headers(customer)
    )
    assert response.status_code == 422


def test_agents_cannot_create_customer_tickets(client, agent):
    response = client.post(
        "/api/tickets",
        json={"subject": "Agent ticket", "description": "Agents should not create tickets here."},
        headers=auth_headers(agent),
    )
    assert response.status_code == 403


def test_customer_ticket_isolation(client, customer, other_customer):
    mine = create_ticket(client, customer)
    theirs = create_ticket(client, other_customer, subject="Other customer issue")

    listing = client.get("/api/tickets", headers=auth_headers(customer)).json()
    assert [t["id"] for t in listing["items"]] == [mine["id"]]
    assert listing["total"] == 1

    response = client.get(f"/api/tickets/{theirs['id']}", headers=auth_headers(customer))
    assert response.status_code == 404

    response = client.post(
        f"/api/tickets/{theirs['id']}/messages", json={"message": "hi"}, headers=auth_headers(customer)
    )
    assert response.status_code == 404


def test_agent_sees_all_tickets(client, customer, other_customer, agent):
    create_ticket(client, customer)
    create_ticket(client, other_customer, subject="Billing question here")
    listing = client.get("/api/tickets", headers=auth_headers(agent)).json()
    assert listing["total"] == 2


def test_ticket_filters_search_and_pagination(client, customer, agent):
    first = create_ticket(client, customer, subject="Invoice has wrong VAT number")
    create_ticket(client, customer, subject="Webhook deliveries failing")
    client.patch(f"/api/tickets/{first['id']}", json={"priority": "CRITICAL"}, headers=auth_headers(agent))

    by_search = client.get("/api/tickets", params={"search": "webhook"}, headers=auth_headers(agent)).json()
    assert [t["subject"] for t in by_search["items"]] == ["Webhook deliveries failing"]

    by_priority = client.get("/api/tickets", params={"priority": "CRITICAL"}, headers=auth_headers(agent)).json()
    assert [t["id"] for t in by_priority["items"]] == [first["id"]]

    by_id = client.get("/api/tickets", params={"search": f"#{first['id']}"}, headers=auth_headers(agent)).json()
    assert by_id["items"][0]["id"] == first["id"]

    paged = client.get("/api/tickets", params={"page": 2, "page_size": 1}, headers=auth_headers(agent)).json()
    assert paged["total"] == 2 and paged["pages"] == 2 and len(paged["items"]) == 1

    unassigned = client.get(
        "/api/tickets", params={"assigned_agent": "unassigned"}, headers=auth_headers(agent)
    ).json()
    assert unassigned["total"] == 2


def test_agent_updates_ticket(client, customer, agent):
    ticket = create_ticket(client, customer)
    response = client.patch(
        f"/api/tickets/{ticket['id']}",
        json={"status": "IN_PROGRESS", "priority": "HIGH", "category": "API", "assigned_agent_id": agent.id},
        headers=auth_headers(agent),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["priority"] == "HIGH"
    assert body["category"] == "API"
    assert body["assigned_agent"]["id"] == agent.id


def test_patch_cannot_resolve_without_summary(client, customer, agent):
    ticket = create_ticket(client, customer)
    response = client.patch(f"/api/tickets/{ticket['id']}", json={"status": "RESOLVED"}, headers=auth_headers(agent))
    assert response.status_code == 422


def test_customer_can_only_close_ticket(client, customer):
    ticket = create_ticket(client, customer)
    forbidden = client.patch(
        f"/api/tickets/{ticket['id']}", json={"priority": "CRITICAL"}, headers=auth_headers(customer)
    )
    assert forbidden.status_code == 403

    closed = client.patch(f"/api/tickets/{ticket['id']}", json={"status": "CLOSED"}, headers=auth_headers(customer))
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    reply = client.post(
        f"/api/tickets/{ticket['id']}/messages", json={"message": "one more thing"}, headers=auth_headers(customer)
    )
    assert reply.status_code == 409


def test_conversation_flow_updates_status(client, customer, agent):
    ticket = create_ticket(client, customer)
    agent_reply = client.post(
        f"/api/tickets/{ticket['id']}/messages", json={"message": "Can you share logs?"}, headers=auth_headers(agent)
    ).json()
    assert agent_reply["status"] == "WAITING_FOR_CUSTOMER"
    assert agent_reply["assigned_agent"]["id"] == agent.id

    customer_reply = client.post(
        f"/api/tickets/{ticket['id']}/messages", json={"message": "Attached logs."}, headers=auth_headers(customer)
    ).json()
    assert customer_reply["status"] == "IN_PROGRESS"
    assert [m["message_type"] for m in customer_reply["messages"]] == ["CUSTOMER", "AGENT", "CUSTOMER"]


def test_assign_ticket_to_self(client, customer, agent, admin):
    ticket = create_ticket(client, customer)
    response = client.post(f"/api/tickets/{ticket['id']}/assign", headers=auth_headers(agent))
    assert response.status_code == 200
    assert response.json()["assigned_agent"]["id"] == agent.id
    assert response.json()["status"] == "IN_PROGRESS"

    # Agents cannot assign to someone else; admins can.
    forbidden = client.post(
        f"/api/tickets/{ticket['id']}/assign", json={"agent_id": admin.id}, headers=auth_headers(agent)
    )
    assert forbidden.status_code == 403
    allowed = client.post(
        f"/api/tickets/{ticket['id']}/assign", json={"agent_id": agent.id}, headers=auth_headers(admin)
    )
    assert allowed.status_code == 200


def test_customer_cannot_assign_or_resolve(client, customer):
    ticket = create_ticket(client, customer)
    assert client.post(f"/api/tickets/{ticket['id']}/assign", headers=auth_headers(customer)).status_code == 403
    response = client.post(
        f"/api/tickets/{ticket['id']}/resolve",
        json={"resolution_summary": "Fixed it"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 403


def test_resolve_ticket_stores_embedding(client, db, customer, agent):
    ticket = create_ticket(client, customer)
    response = client.post(
        f"/api/tickets/{ticket['id']}/resolve",
        json={"resolution_summary": "Customer used a sandbox key; issued a live key."},
        headers=auth_headers(agent),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RESOLVED"
    assert body["resolved_at"] is not None
    assert body["messages"][-1]["message_type"] == "SYSTEM"

    embedding = db.query(TicketEmbedding).filter_by(ticket_id=ticket["id"]).one()
    assert "sandbox key" in embedding.resolution_summary

    again = client.post(
        f"/api/tickets/{ticket['id']}/resolve",
        json={"resolution_summary": "Again"},
        headers=auth_headers(agent),
    )
    assert again.status_code == 409


def test_customer_reply_reopens_resolved_ticket(client, customer, agent):
    ticket = create_ticket(client, customer)
    client.post(
        f"/api/tickets/{ticket['id']}/resolve",
        json={"resolution_summary": "Rotated the key."},
        headers=auth_headers(agent),
    )
    reopened = client.post(
        f"/api/tickets/{ticket['id']}/messages", json={"message": "Still broken"}, headers=auth_headers(customer)
    ).json()
    assert reopened["status"] == "OPEN"
    assert reopened["resolved_at"] is None


def test_ticket_analytics_are_real(client, customer, agent):
    first = create_ticket(client, customer)
    create_ticket(client, customer, subject="Second ticket subject")
    client.patch(f"/api/tickets/{first['id']}", json={"priority": "CRITICAL", "category": "API"}, headers=auth_headers(agent))
    client.post(
        f"/api/tickets/{first['id']}/resolve", json={"resolution_summary": "Done and dusted"}, headers=auth_headers(agent)
    )

    stats = client.get("/api/analytics/tickets", headers=auth_headers(agent)).json()
    assert stats["total_tickets"] == 2
    assert stats["open_tickets"] == 1
    assert stats["resolved_tickets"] == 1
    assert stats["critical_tickets"] == 0  # the critical one is resolved
    assert stats["tickets_by_category"]["API"] == 1
    assert stats["average_resolution_time_hours"] is not None


def test_invalid_ticket_returns_404(client, agent):
    assert client.get("/api/tickets/9999", headers=auth_headers(agent)).status_code == 404
