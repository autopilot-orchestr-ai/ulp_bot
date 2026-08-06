import yaml
from langchain_core.documents import Document
from src.ai.knowledge.store import KnowledgeStore


async def load_faq(faq_path: str, store: KnowledgeStore) -> int:
    """Load FAQ YAML into the knowledge store. Returns number of entries loaded."""
    with open(faq_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return 0

    docs = []
    doc_idx = 0

    for lang, items in data.items():
        for item in items:
            docs.append(
                Document(
                    page_content=f"Q: {item['question']}\nA: {item['answer']}",
                    metadata={
                        "source": "faq", 
                        "question": item["question"],
                        "lang": lang  
                    },
                )
            )
            doc_idx += 1

    ids = [f"faq_{i}" for i in range(len(docs))]
    await store.add_documents(docs, ids=ids)
    return len(docs)