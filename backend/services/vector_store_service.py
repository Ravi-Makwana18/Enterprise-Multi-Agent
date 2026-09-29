import logging
import os
from typing import Any

import chromadb

logger = logging.getLogger(__name__)

# Persist Chroma DB in backend/data/chroma_db by default
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db"))
os.makedirs(CHROMA_DIR, exist_ok=True)

_client = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Singleton Chroma persistent client instance."""
    global _client
    if _client is None:
        try:
            _client = chromadb.PersistentClient(path=os.path.abspath(CHROMA_DIR))
            logger.info("ChromaDB vector store initialized at: %s", os.path.abspath(CHROMA_DIR))
        except Exception as exc:
            logger.error("Failed to initialize ChromaDB PersistentClient: %s", exc)
            _client = chromadb.Client()
    return _client


def get_or_create_collection(collection_name: str = "enterprise_knowledge"):
    """Retrieve or create a Chroma collection with default embeddings."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(
    documents: list[str],
    metadatas: list[dict[str, Any]] | None = None,
    ids: list[str] | None = None,
    collection_name: str = "enterprise_knowledge",
) -> None:
    """Store text documents with metadata into the vector store."""
    if not documents:
        return

    collection = get_or_create_collection(collection_name)
    if ids is None:
        import uuid
        ids = [f"doc-{uuid.uuid4().hex[:8]}" for _ in documents]

    if metadatas is None:
        metadatas = [{"source": "manual"} for _ in documents]

    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info("Upserted %d documents into vector store [%s]", len(documents), collection_name)


def search_similar(
    query: str,
    n_results: int = 3,
    collection_name: str = "enterprise_knowledge",
    where: dict[str, Any] | None = None,
    min_similarity: float = 0.52,
) -> list[dict[str, Any]]:
    """Retrieve top-k semantically similar documents matching the query with minimum similarity threshold."""
    try:
        collection = get_or_create_collection(collection_name)
        count = collection.count()
        if count == 0:
            return []

        limit = min(n_results * 2, count)
        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": limit,
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)
        matched_docs: list[dict[str, Any]] = []

        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]

            for i, doc in enumerate(docs):
                dist = distances[i] if i < len(distances) and distances[i] is not None else 1.0
                sim = round(1.0 - dist, 4)
                # Only include genuinely similar documents (reject distant / irrelevant hits)
                if sim < min_similarity:
                    continue
                matched_docs.append({
                    "id": ids[i] if i < len(ids) else None,
                    "content": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "similarity": sim,
                })
                if len(matched_docs) >= n_results:
                    break
        return matched_docs
    except Exception as exc:
        logger.warning("Vector search failed on [%s]: %s", collection_name, exc)
        return []


def cleanup_contaminated_knowledge(collection_name: str = "enterprise_knowledge") -> int:
    """Purge temporary tickets or uncurated user interactions that were accidentally indexed."""
    try:
        col = get_or_create_collection(collection_name)
        all_items = col.get()
        if all_items and all_items.get("ids"):
            ticket_ids = [doc_id for doc_id in all_items["ids"] if doc_id.startswith("ticket-")]
            if ticket_ids:
                col.delete(ids=ticket_ids)
                logger.info("Purged %d contaminated ticket records from [%s]", len(ticket_ids), collection_name)
                return len(ticket_ids)
        return 0
    except Exception as exc:
        logger.warning("Failed to clean up contaminated knowledge: %s", exc)
        return 0



def seed_default_knowledge() -> None:
    """Pre-populate enterprise knowledge base if empty."""
    collection = get_or_create_collection("enterprise_knowledge")
    if collection.count() > 0:
        return

    default_knowledge = [
        # Support / IT FAQs
        (
            "VPN Connection Troubleshooting: If unable to connect to the corporate GlobalProtect or OpenVPN server, "
            "clear the local DNS cache using 'ipconfig /flushdns', verify MFA in Authenticator app, restart the service, "
            "and switch protocol from UDP to TCP port 443 if behind an aggressive firewall.",
            {"category": "it", "topic": "vpn", "service": "support"},
            "kb-vpn-01",
        ),
        (
            "SSO and Identity Access: For Azure AD / Okta sign-in errors like AADSTS50020 or 'account locked', "
            "users must wait 15 minutes for temporary lockout to expire or submit a self-service password reset "
            "at identity.internal. Admin approval is required for privileged groups.",
            {"category": "access", "topic": "sso_auth", "service": "support"},
            "kb-sso-01",
        ),
        (
            "Corporate Database Connectivity: Connection timeouts to production MySQL/PostgreSQL clusters require "
            "verifying the client IP is whitelisted in the security group and that SSH bastion tunnels use port 2222.",
            {"category": "database", "topic": "db_connectivity", "service": "support"},
            "kb-db-01",
        ),
        # Security & Compliance
        (
            "Personnel Security Verification Policy (ISO 27001 / SOC 2): All enterprise contractors and employees "
            "must submit a verified government photo ID (Aadhaar or Passport) and cleared police background check before "
            "receiving production credentials. Pending police checks limit access to sandbox environments only.",
            {"category": "compliance", "topic": "background_check", "service": "security"},
            "kb-sec-01",
        ),
        (
            "ID Verification Standards: Aadhaar must be exactly 12 numeric digits with name matching offer letter. "
            "Passports must have at least 6 months validity. Address proof must be dated within 90 days.",
            {"category": "compliance", "topic": "id_standards", "service": "security"},
            "kb-sec-02",
        ),
        # Payroll & Salary
        (
            "Enterprise Compensation Guidelines: Standard House Rent Allowance (HRA) benchmark is between 20% and 50% "
            "of Basic Salary. Bonus incentives exceeding 25% of annual gross require executive escalation and board audit.",
            {"category": "payroll", "topic": "hra_bonus_policy", "service": "salary"},
            "kb-sal-01",
        ),
        (
            "Tax Withholding & PAN Requirements: Under corporate tax regulations, a standard 10% withholding applies "
            "to eligible gross compensation. Non-furnishing of a valid PAN mandates maximum marginal rate withholding.",
            {"category": "payroll", "topic": "tax_withholding", "service": "salary"},
            "kb-sal-02",
        ),
    ]

    docs = [item[0] for item in default_knowledge]
    metas = [item[1] for item in default_knowledge]
    ids = [item[2] for item in default_knowledge]

    collection.add(
        documents=docs,
        metadatas=metas,
        ids=ids,
    )
    logger.info("Seeded %d default enterprise knowledge items into ChromaDB.", len(docs))
