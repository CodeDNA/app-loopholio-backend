import uuid
import chromadb
from chromadb.utils import embedding_functions

chroma_client = chromadb.PersistentClient(path="./chroma_db")

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = chroma_client.get_or_create_collection(
    name="tos_documents", embedding_function=sentence_transformer_ef
)


def store_chunks_in_db(chunks: list[dict], source_name: str):
    documents = []
    metadatas = []
    ids = []

    for chunk in chunks:
        documents.append(chunk["section_text"])
        metadatas.append(
            {
                "chunk_id": chunk["chunk_id"],
                "section_title": chunk["section_title"],
                "source_file": source_name,
            }
        )
        ids.append(str(uuid.uuid4()))

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return len(documents)


def retrieve_chunks(query: str, n_results: int = 3):
    # TODO: Implement the code to use this in subsequent user queries
    """
    Searches the VectorDB according to the user query
    """
    results = collection.query(query_texts=[query], n_results=n_results)
    return results
