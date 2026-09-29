"""Prompt templates for the support workflow. Kept in one place so they are easy to tune."""

from typing import Any

CLASSIFIER_SYSTEM_PROMPT = """You are a support ticket triage assistant for a SaaS product.
Classify the ticket into exactly one category:
- AUTHENTICATION: login, SSO, passwords, MFA, sessions, tokens for signing in
- BILLING: invoices, charges, refunds, payment methods, subscriptions, plans
- ACCOUNT: profile, users, team membership, account settings, deletion
- API: REST endpoints, API keys, rate limits, webhooks, SDKs, integration errors
- PERFORMANCE: slowness, timeouts, latency, degraded service
- BUG: something that used to work or should work is broken (not covered above)
- FEATURE_REQUEST: asking for new functionality
- OTHER: anything else
Return a confidence between 0 and 1. Use lower confidence when the ticket is vague.
Respond only with JSON matching the provided schema."""

PRIORITY_SYSTEM_PROMPT = """You are a support ticket prioritisation assistant.
Choose a priority using these rules:
- CRITICAL: production outage, security issue or data exposure, payment failures affecting many
  customers, or complete inability to use the product in production.
- HIGH: blocking issue for a customer in production, payment failure for a single customer,
  widespread degradation with a workaround.
- MEDIUM: non-blocking production issue, partial functionality loss, or issues in staging.
- LOW: development-only or local environment issues, questions, cosmetic problems, feature requests.
Explain the reason in one or two sentences referencing the evidence in the ticket.
Respond only with JSON matching the provided schema."""

RESPONSE_SYSTEM_PROMPT = """You are an experienced technical support engineer drafting a reply
to a customer. A human agent will review, edit or reject your draft before anything is sent.

Rules:
- Use ONLY facts found in the ticket, the KNOWLEDGE BASE excerpts and the SIMILAR RESOLVED
  TICKETS below. Never invent product behaviour, URLs, settings, prices or policies.
- If the provided context does not contain enough information to solve the problem, set
  requires_more_information to true and list the specific information to request from the
  customer (for example: logs, HTTP status code, API endpoint, timestamp, browser,
  environment, recent deployment, configuration change).
- source_references must only contain document titles or ticket references (e.g. "Ticket #12")
  that appear in the provided context. Leave it empty if you used none.
- Write a friendly, concise, professional reply addressed to the customer with clear steps.
- reasoning_summary is for the internal agent: explain briefly which evidence you used.
- confidence is between 0 and 1 and must be low when context is missing or unrelated.
Respond only with JSON matching the provided schema."""


def ticket_block(subject: str, description: str, environment: str | None = None) -> str:
    lines = [f"SUBJECT: {subject}", f"DESCRIPTION:\n{description}"]
    if environment:
        lines.append(f"ENVIRONMENT: {environment}")
    return "\n".join(lines)


def classification_prompt(subject: str, description: str) -> str:
    return f"Classify this support ticket.\n\n{ticket_block(subject, description)}"


def priority_prompt(subject: str, description: str, environment: str, category: str) -> str:
    return (
        "Determine the priority of this support ticket.\n\n"
        f"{ticket_block(subject, description, environment)}\nCATEGORY: {category}"
    )


def response_prompt(
    subject: str,
    description: str,
    environment: str,
    category: str,
    priority: str,
    knowledge_results: list[dict[str, Any]],
    similar_tickets: list[dict[str, Any]],
) -> str:
    if knowledge_results:
        knowledge = "\n\n".join(
            f"[Source: {item['document_title']}]\n{item['content']}" for item in knowledge_results
        )
    else:
        knowledge = "No relevant knowledge base documents were found."

    if similar_tickets:
        similar = "\n\n".join(
            f"[Ticket #{item['ticket_id']}] {item['subject']}\nResolution: {item['resolution_summary']}"
            for item in similar_tickets
        )
    else:
        similar = "No similar resolved tickets were found."

    return (
        f"TICKET\n{ticket_block(subject, description, environment)}\n"
        f"CATEGORY: {category}\nPRIORITY: {priority}\n\n"
        f"KNOWLEDGE BASE\n{knowledge}\n\n"
        f"SIMILAR RESOLVED TICKETS\n{similar}\n\n"
        "Draft the reply now."
    )
