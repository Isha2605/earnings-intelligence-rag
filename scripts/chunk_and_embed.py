import os
import json
from chromadb import PersistentClient
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# ── paths ──────────────────────────────────────────────────────────────────
PROCESSED_DIR   = "data/processed"
VECTORSTORE_DIR = "vectorstore/chroma_db"

FILES = {
    2022: "msft_10k_2022.txt",
    2023: "msft_10k_2023.txt",
    2024: "msft_10k_2024.txt",
}

# ── setup embedding model ──────────────────────────────────────────────────
print("Loading embedding model...")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.embed_model = embed_model
Settings.llm = None  # we are not using llama_index's LLM here
print("Embedding model loaded!")

# ── setup chromadb ─────────────────────────────────────────────────────────
os.makedirs(VECTORSTORE_DIR, exist_ok=True)
chroma_client = PersistentClient(path=VECTORSTORE_DIR)

# clear existing collection so we start fresh each run
try:
    chroma_client.delete_collection("msft_10k")
    print("Cleared existing collection")
except:
    pass

collection = chroma_client.get_or_create_collection("msft_10k")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)


# ── chunking function ──────────────────────────────────────────────────────
def chunk_text(text, chunk_size=1500, overlap=150):
    """
    Split text into overlapping chunks.
    chunk_size: characters per chunk (approx 512 tokens)
    overlap: characters shared between consecutive chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # try to end at a sentence boundary
        # so we don't cut mid-sentence
        if end < len(text):
            last_period = text.rfind(".", start, end)
            last_newline = text.rfind("\n", start, end)
            boundary = max(last_period, last_newline)
            if boundary > start + (chunk_size // 2):
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap  # overlap with next chunk

    return chunks


# ── main ───────────────────────────────────────────────────────────────────
def run():
    all_documents = []

    for year, filename in FILES.items():
        filepath = os.path.join(PROCESSED_DIR, filename)

        print(f"\nProcessing FY{year}...")

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        print(f"  Created {len(chunks)} chunks")

        # convert each chunk to a LlamaIndex Document
        # with metadata so we know which year it came from
        for i, chunk in enumerate(chunks):
            doc = Document(
                text=chunk,
                metadata={
                    "fiscal_year": year,
                    "source": f"msft_10k_{year}",
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                }
            )
            all_documents.append(doc)

    print(f"\nTotal documents to embed: {len(all_documents)}")
    print("Building vector index... (this may take a few minutes)")

    # build the index — this embeds every chunk and stores in ChromaDB
    index = VectorStoreIndex.from_documents(
        all_documents,
        storage_context=storage_context,
        show_progress=True
    )

    print("\nVector index built successfully!")
    print(f"ChromaDB saved to: {VECTORSTORE_DIR}")

    # quick sanity check — run a test query
    print("\nRunning test query...")
    retriever = index.as_retriever(similarity_top_k=3)
    results = retriever.retrieve("What was Azure revenue growth?")

    print(f"Test query returned {len(results)} results:")
    for i, node in enumerate(results):
        print(f"\n  Result {i+1} (score: {node.score:.3f}):")
        print(f"  Year: {node.metadata.get('fiscal_year')}")
        print(f"  Text: {node.text[:150]}...")


if __name__ == "__main__":
    run()