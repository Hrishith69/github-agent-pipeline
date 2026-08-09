import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from state import AgentState
from retriever import get_relevant_docs

# Initialize Gemini LLM using Flash model for speed & cost efficiency
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0,
    google_api_key=api_key
)

# --- WORKER 1: CLASSIFY NODE ---
def classify_node(state: AgentState) -> dict:
    """Categorizes the issue as Bug, Question, Feature Request, or Other."""
    prompt = f"""
    You are an expert GitHub issue triage assistant.
    Analyze the issue and classify it into EXACTLY ONE category:
    - Bug
    - Question
    - Feature Request
    - Other

    Title: {state['title']}
    Body: {state['body']}

    Respond ONLY with the category name.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    category = response.content.strip()
    print(f"🏷️ [Classify] Category: {category}")
    return {"category": category}

# --- WORKER 2: RETRIEVE NODE ---
def retrieve_node(state: AgentState) -> dict:
    """Fetches relevant FastAPI documentation chunks from ChromaDB."""
    query = f"{state['title']} {state['body']}"
    docs = get_relevant_docs(query)
    print(f"📚 [Retrieve] Found {len(docs)} context chunks.")
    return {"retrieved_docs": docs}

# --- WORKER 3: DRAFT NODE ---
def draft_node(state: AgentState) -> dict:
    """Generates a technical response using retrieved documentation."""
    context = "\n---\n".join(state["retrieved_docs"])
    prompt = f"""
    You are an automated technical support engineer for this repository.
    Use ONLY the documentation context provided below to answer the user's issue.
    If the context does not contain enough detail, explain what is available and offer general guidance.

    Issue Title: {state['title']}
    Issue Body: {state['body']}

    Documentation Context:
    {context}

    Write a helpful, professional markdown response.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    draft = response.content.strip()
    print("📝 [Draft] Response created.")
    return {"draft_response": draft}

# --- WORKER 4: CONFIDENCE CHECK NODE ---
def confidence_check_node(state: AgentState) -> dict:
    """Evaluates answer quality and assigns a confidence score."""
    draft = state.get("draft_response", "")
    docs = state.get("retrieved_docs", [])
    
    # Simple rule-based confidence evaluation
    if len(docs) > 0 and len(draft) > 50:
        score = 0.95
        status = "DRAFTED"
    else:
        score = 0.40
        status = "NEEDS_HUMAN_REVIEW"
        
    print(f"📊 [Confidence] Score: {score} | Status: {status}")
    return {"confidence_score": score, "status": status}