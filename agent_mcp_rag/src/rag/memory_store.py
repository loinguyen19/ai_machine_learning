from __future__ import annotations
import chromadb
from paths import CHROMA_DIR

COLLECTION_NAME = "client_chat_memory"


class MemoryStore:
    def __init__(self, persist_dir: str | None = None) -> None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir or str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)

    def add_documents(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def search(
        self,
        query: str,
        *,
        client_id: str | None = None,
        n_results: int = 5,
    ) -> list[dict]:
        where = {"client_id": client_id} if client_id else None
        results = self._collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        hits: list[dict] = []
        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]
        for doc, meta, dist in zip(documents[0], metadatas[0], distances[0]):
            hits.append(
                {
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                }
            )
        return hits

    def collection_count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)
