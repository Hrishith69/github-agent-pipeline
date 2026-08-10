import os
import sys
import io

# Fix Windows terminal emoji/unicode crash (cp1252 -> utf-8)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(override=True)

from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import (
    classify_node,
    retrieve_node,
    draft_node,
    confidence_check_node
)

# 1. Initialize the State Graph using our clipboard schema
workflow = StateGraph(AgentState)

# 2. Register the 4 workers (Nodes)
workflow.add_node("classify", classify_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("draft", draft_node)
workflow.add_node("confidence_check", confidence_check_node)

# 3. Connect the assembly line (Edges)
workflow.add_edge(START, "classify")
workflow.add_edge("classify", "retrieve")
workflow.add_edge("retrieve", "draft")
workflow.add_edge("draft", "confidence_check")
workflow.add_edge("confidence_check", END)

# 4. Compile the graph into an executable application
app = workflow.compile()

# --- STANDALONE TEST RUNNER ---
if __name__ == "__main__":
    # Sample GitHub issue simulating an incoming user request
    test_issue = {
        "issue_number": 101,
        "title": "FastAPI 500 Internal Server Error when handling request",
        "body": "I am receiving an HTTP 500 validation error when sending a request payload. How do I inspect HTTPValidationError details?",
        "category": None,
        "retrieved_docs": [],
        "draft_response": None,
        "confidence_score": 0.0,
        "status": "NEW"
    }

    print("🚀 Running LangGraph Core Agent Pipeline...\n")
    
    # Execute the entire graph end-to-end
    final_state = app.invoke(test_issue)

    print("\n================ 🏁 FINAL AGENT OUTPUT 🏁 ================")
    print(f"📌 Issue #{final_state['issue_number']}: {final_state['title']}")
    print(f"🏷️ Category: {final_state['category']}")
    print(f"📊 Confidence Score: {final_state['confidence_score']}")
    print(f"🚦 Status: {final_state['status']}")
    print("\n📝 Drafted Response:")
    print("--------------------------------------------------")
    print(final_state["draft_response"])
    print("--------------------------------------------------")