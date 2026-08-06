from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector


class KnowledgeStore:
    """Thin wrapper around PGVector for the knowledge base."""

    COLLECTION_NAME = "knowledge_base"

    def __init__(self, db_url: str, schema: str, embeddings: Embeddings):
        # PGVector requires psycopg driver, not asyncpg
        pg_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

        self._store = PGVector(
            embeddings=embeddings,
            collection_name=f"{schema}_{self.COLLECTION_NAME}",
            connection=pg_url,
            use_jsonb=True,
            async_mode=True,
        )

    async def add_documents(
        self,
        docs: list[Document],
        ids: list[str] | None = None
    ) -> None:
        await self._store.aadd_documents(docs, ids=ids)

    async def search(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7,
        filter: dict | None = None
    ) -> list[Document]:
        results = await self._store.asimilarity_search_with_relevance_scores(
            query, k=k, filter=filter
        )
        return [doc for doc, score in results if score >= threshold]