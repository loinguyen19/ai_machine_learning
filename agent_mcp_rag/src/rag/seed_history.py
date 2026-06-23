from __future__ import annotations
import json
from paths import MOCK_HISTORY_PATH
from rag.memory_store import MemoryStore


def _pair_messages(messages: list[dict]) -> list[dict]:
    """Group consecutive user+assistant turns into single RAG documents."""
    pairs: list[dict] = []
    i = 0
    while i < len(messages):
        current = messages[i]
        if current["role"] == "user" and i + 1 < len(messages):
            nxt = messages[i + 1]
            if nxt["role"] == "assistant" and current["client_id"] == nxt["client_id"]:
                pairs.append(
                    {
                        "client_id": current["client_id"],
                        "session_id": current["session_id"],
                        "content": (
                            f"User: {current['content']}\n"
                            f"Assistant: {nxt['content']}"
                        ),
                        "tags": list({*current.get("tags", []), *nxt.get("tags", [])}),
                        "timestamp": current.get("timestamp", ""),
                    }
                )
                i += 2
                continue
        pairs.append(
            {
                "client_id": current["client_id"],
                "session_id": current["session_id"],
                "content": f"{current['role'].title()}: {current['content']}",
                "tags": current.get("tags", []),
                "timestamp": current.get("timestamp", ""),
            }
        )
        i += 1
    return pairs


def seed_client_memory(*, force: bool = False) -> dict:
    store = MemoryStore()
    if store.collection_count() > 0 and not force:
        return {
            "status": "skipped",
            "message": "Collection already seeded. Use force=true to re-ingest.",
            "count": store.collection_count(),
        }

    if force:
        store.clear()

    if not MOCK_HISTORY_PATH.exists():
        return {"status": "error", "message": f"Mock history not found: {MOCK_HISTORY_PATH}"}

    payload = json.loads(MOCK_HISTORY_PATH.read_text(encoding="utf-8"))
    messages = payload.get("messages", [])

    by_client: dict[str, list[dict]] = {}
    for msg in messages:
        by_client.setdefault(msg["client_id"], []).append(msg)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for client_id, client_msgs in by_client.items():
        pairs = _pair_messages(client_msgs)
        for idx, pair in enumerate(pairs):
            doc_id = f"{client_id}_{pair['session_id']}_{idx}"
            ids.append(doc_id)
            documents.append(pair["content"])
            metadatas.append(
                {
                    "client_id": client_id,
                    "session_id": pair["session_id"],
                    "tags": ",".join(pair.get("tags", [])),
                    "timestamp": pair.get("timestamp", ""),
                }
            )

    store.add_documents(ids=ids, documents=documents, metadatas=metadatas)
    return {
        "status": "seeded",
        "message": f"Ingested {len(documents)} documents into Chroma.",
        "count": store.collection_count(),
    }


def load_client_profiles() -> dict:
    if not MOCK_HISTORY_PATH.exists():
        return {}
    payload = json.loads(MOCK_HISTORY_PATH.read_text(encoding="utf-8"))
    return payload.get("clients", {})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed client chat memory into Chroma.")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if data exists.")
    args = parser.parse_args()
    result = seed_client_memory(force=args.force)
    print(result)
