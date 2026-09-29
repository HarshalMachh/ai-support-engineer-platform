from app.ai.embeddings import EmbeddingError, get_embedding_provider
from app.ai.text_processing import clean_text, split_into_chunks
from app.main import app
from tests.conftest import auth_headers

BILLING_DOC = b"""# Billing and Refunds

Annual plans may be refunded in full within 14 days of purchase.

Failed card payments are retried after 3, 5 and 7 days before a 14-day grace period.
"""


def _upload(client, user, name="billing.md", content=BILLING_DOC, content_type="text/markdown"):
    return client.post(
        "/api/knowledge/documents",
        files={"file": (name, content, content_type)},
        headers=auth_headers(user),
    )


def test_admin_uploads_markdown_document(client, admin):
    response = _upload(client, admin)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Billing and Refunds"
    assert body["filename"] == "billing.md"
    assert body["chunk_count"] >= 1
    assert body["embedding_model"] == "hash-embedding"


def test_agent_cannot_upload_documents(client, agent):
    assert _upload(client, agent).status_code == 403


def test_upload_rejects_unsupported_extension(client, admin):
    response = _upload(client, admin, name="malware.exe", content=b"MZ....", content_type="application/octet-stream")
    assert response.status_code == 422
    assert ".txt and .md" in response.json()["detail"]


def test_upload_rejects_non_utf8_and_binary(client, admin):
    assert _upload(client, admin, name="bad.txt", content=b"\xff\xfe\xfa" * 20, content_type="text/plain").status_code == 422
    assert _upload(client, admin, name="bin.txt", content=b"abc\x00def" * 10, content_type="text/plain").status_code == 422


def test_upload_rejects_empty_and_oversized(client, admin, monkeypatch):
    assert _upload(client, admin, content=b"").status_code == 422
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_BYTES", 50)
    assert _upload(client, admin).status_code == 422


def test_upload_sanitizes_filename(client, admin):
    response = _upload(client, admin, name="../../etc/pass wd.txt", content=b"Some useful plain text content here.")
    assert response.status_code == 201
    assert response.json()["filename"] == "pass_wd.txt"


def test_list_get_and_delete_documents(client, admin, agent):
    document_id = _upload(client, admin).json()["id"]

    listing = client.get("/api/knowledge/documents", headers=auth_headers(agent))
    assert listing.status_code == 200
    assert [d["id"] for d in listing.json()] == [document_id]

    detail = client.get(f"/api/knowledge/documents/{document_id}", headers=auth_headers(agent)).json()
    assert detail["chunks"][0]["chunk_index"] == 0
    assert "refunded" in detail["content"]

    assert client.delete(f"/api/knowledge/documents/{document_id}", headers=auth_headers(agent)).status_code == 403
    assert client.delete(f"/api/knowledge/documents/{document_id}", headers=auth_headers(admin)).status_code == 204
    assert client.get(f"/api/knowledge/documents/{document_id}", headers=auth_headers(admin)).status_code == 404


def test_semantic_search_returns_relevant_chunks(client, admin, agent):
    _upload(client, admin)
    _upload(
        client,
        admin,
        name="auth.md",
        content=b"# Login Help\n\nReset your password with the Forgot password link. MFA codes depend on the clock.",
    )
    response = client.post(
        "/api/knowledge/search", json={"query": "refund annual plan", "top_k": 2}, headers=auth_headers(agent)
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["document_title"] == "Billing and Refunds"
    assert results[0]["similarity"] > results[-1]["similarity"]


def test_search_returns_503_when_embeddings_fail(client, agent):
    class BrokenEmbedder:
        model_name = "broken"
        dimension = 768

        def embed(self, texts):
            raise EmbeddingError("Could not reach Ollama for embeddings")

    app.dependency_overrides[get_embedding_provider] = lambda: BrokenEmbedder()
    response = client.post("/api/knowledge/search", json={"query": "refund"}, headers=auth_headers(agent))
    assert response.status_code == 503
    assert response.json()["code"] == "embedding_failed"


def test_clean_text_and_chunking_with_overlap():
    long_paragraph = " ".join(f"w{i}" for i in range(300))
    text = clean_text("Title\r\n\r\n\r\n\r\nPara one.\x07  \n\n" + long_paragraph)
    assert "\x07" not in text and "\n\n\n" not in text

    chunks = split_into_chunks(text, chunk_size=300, overlap=60)
    assert len(chunks) > 3
    assert all(len(c) <= 300 for c in chunks)
    # Consecutive chunks of the long paragraph share whole words (no mid-word splits).
    assert chunks[2].split()[0] in chunks[1].split()
    assert all(word.startswith("w") for chunk in chunks[1:] for word in chunk.split())
