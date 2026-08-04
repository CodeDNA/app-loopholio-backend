from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
import operator

class Sections(TypedDict):
    title: str
    text: str
    context: str

# Shared state schema - LangGraph State
class ToSAgentState(TypedDict):
    # User's query
    sections: List[dict]

    # Chunks retrieved from ChromaDB
    # retrieved_chunks: List[Dict[str, Any]]

    # Output from Clause Extraction Agent
    extracted_clauses: Annotated[list, operator.add]

    # Output from Risk Detection Agent
    risk_analysis: Annotated[list, operator.add]

    # Output from Explainer Agent with citations
    explanations: Annotated[list, operator.add]

    # Output from Final Report Generator Agent - Also Frontend contract
    final_report: list[Dict[str, Any]]


# Frontend Response schema
class RiskReportItem(TypedDict):
    level: str = Field(description="Choose one from High, Medium, or Low risk level")
    confidence: int = Field(description="Confidence score between 0 and 100")
    category: str = Field(description="Risk Category: Category of the legal clause")
    reason: str = Field(description="Reason why this is flagged")
    whyMatters: str = Field(description="Simple explanation of why it matters to the user")
    recommendation: str = Field(description="Actionable advice for the user")
    exactClause: str = Field(description="Verbatim/Quoted text from the document")

class FinalReportSchema(BaseModel):
    risks: List[RiskReportItem]