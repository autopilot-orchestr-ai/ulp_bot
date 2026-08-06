from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
# from langchain_community.embeddings import HuggingFaceEmbeddings


def get_embeddings(model: str, **kwargs) -> Embeddings:
    return OpenAIEmbeddings(model=model, **kwargs)


