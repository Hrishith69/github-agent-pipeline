import os
from dotenv import load_dotenv

# Force load_dotenv to OVERWRITE any existing Windows system variables
load_dotenv(override=True)

# Extract key from .env
api_key = os.getenv("GEMINI_API_KEY") 

if not api_key:
    raise ValueError("[ERROR] No API key found! Please check your .env file.")

# Force set both variables in Python's live environment memory
os.environ["GEMINI_API_KEY"] = api_key

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Visual Verification: Prints masked key so you can confirm Python sees your key
masked_key = f"{api_key[:6]}...{api_key[-4:]}"
print(f"[Key Check] Using Key: {masked_key}")

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db1")

# Initialize embeddings with the verified key
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2",
    google_api_key=api_key
)

vector_store = Chroma(
    persist_directory=CHROMA_PATH, 
    embedding_function=embeddings
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})

def get_relevant_docs(query: str) -> list[str]:
    """Retrieves relevant documentation chunks for a given issue query."""
    docs = retriever.invoke(query)
    return [doc.page_content for doc in docs]

if __name__ == "__main__":
    test_query = "How to handle FastAPI internal server error?"
    results = get_relevant_docs(test_query)
    print(f"\n[Search] Found {len(results)} relevant documentation chunks:")
    for idx, doc in enumerate(results, 1):
        print(f"\n--- Chunk {idx} ---\n{doc[:200]}...")