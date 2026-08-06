from typing import List, Dict, Any, Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
import operator
from enum import Enum


# LangGraph State
class ToSAgentState(TypedDict):
    # User's query
    sections: List[dict]  # chunks created by the chunker

    # Chunks retrieved from ChromaDB
    # retrieved_chunks: List[Dict[str, Any]]

    # Output from Clause Extraction Agent
    extracted_clauses: Annotated[list, operator.add]

    # Output from Risk Detection Agent
    detected_risks: Annotated[list, operator.add]

    # Output from Explainer Agent with citations
    explanations: Annotated[list, operator.add]

    # Output from Final Report Generator Agent - Also Frontend contract
    final_report: list[Dict[str, Any]]


class ClauseType(str, Enum):
    ACCEPTANCE = "Acceptance of Terms"
    ELIGIBILITY = "Eligibility"
    ACCOUNT = "Account Registration"
    PAYMENT = "Payment"
    ACCEPTABLE_USE = "Acceptable Use"
    TERMINATION = "Termination"
    LIABILITY = "Limitation of Liability"
    WARRANTY = "Disclaimer of Warranties"
    INTELLECTUAL_PROPERTY = "Intellectual Property"
    INDEMNIFICATION = "Indemnification"
    PRIVACY = "Privacy"
    GOVERNING_LAW = "Governing Law"
    DISPUTE_RESOLUTION = "Dispute Resolution"
    MODIFICATION = "Modification of Terms"
    OTHER = "Other"


class ExtractedClause(BaseModel):
    clause_type: ClauseType = Field(
        description="Broad contractual category describing the primary function of the clause."
    )
    clause_text: str = Field(
        description="Contractual language extracted from the supplied section text."
        "It must preserve the source wording and legal meaning without explanation."
    )


class ClauseExtractionOutput(BaseModel):
    clauses: list[ExtractedClause]


class RiskLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RiskCategory(str, Enum):
    PAYMENT = "Payment"
    LIABILITY = "Limitation of Liability"
    TERMINATION = "Termination"
    PRIVACY = "Privacy"
    REFUND = "Refund"
    ARBITRATION = "Arbitration"


class DetectedRisks(BaseModel):
    level: RiskLevel | None = None
    risk_found: bool = Field(
        description="Whether the clause creates a meaningful legal risk."
    )
    confidence: int | None = None
    category: RiskCategory | None = None
    reason: str | None = None
    evidence: str | None = None


# Frontend Response schema
class RiskReportItem(BaseModel):
    chunk_id: str = Field(description="Id of the chunk which produced this report item")
    level: str = Field(description="Choose one from High, Medium, or Low risk level")
    confidence: int = Field(description="Confidence score between 0 and 100")
    category: str = Field(description="Risk Category: Category of the legal clause")
    reason: str = Field(description="Reason why this is flagged")
    whyMatters: str = Field(
        description="Simple explanation of why it matters to the user"
    )
    recommendation: str = Field(description="Actionable advice for the user")
    exactClause: str = Field(description="Verbatim/Quoted text from a section")
    source_text: str = Field(description="Verbatim/Quoted section from the document")


class ExplainedRisk(BaseModel):
    whyMatters: str
    recommendation: str


class FinalReportSchema(BaseModel):
    risks: List[RiskReportItem]


initial_graph_state = {
    "sections": [],
    # "retrieved_chunks": [],
    "extracted_clauses": [],
    "detected_risks": [],
    "plain_explanations": [],
    "final_report": [],
}
