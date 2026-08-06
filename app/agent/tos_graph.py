import json
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.tos_agent_states import (
    ToSAgentState,
    DetectedRisks,
    ClauseExtractionOutput,
    ExplainedRisk,
)
from langgraph.types import Send
from app.llm.llm_factory import get_llm
from app.agent.all_instructions import (
    clause_extraction_instruction,
    risk_detection_instruction,
    explanation_instruction,
)

llm = get_llm()

def route_to_clause_extraction(state: ToSAgentState):
    return [
        Send("clause_extraction", {"section": section}) for section in state["sections"]
    ]

# - - - Agent 1: Clause Extraction Agent - - -
'''
## This agent extract legal clauses from the chunks provided.
## It does not have legal reasoning capability. It only does extraction.
'''
async def clause_extraction_node(state: dict) -> ToSAgentState:
    section = state["section"]
    section_title = section["section_title"]
    section_text = section["section_text"]
    chunk_id = section["chunk_id"]

    clause_extraction_llm_input = {
        "section_title": section_title,
        "section_text": section_text,
    }

    structured_llm = llm.with_structured_output(ClauseExtractionOutput)

    extracted_clauses = await structured_llm.ainvoke(
        [
            SystemMessage(content=clause_extraction_instruction),
            HumanMessage(
                content=json.dumps(
                    clause_extraction_llm_input, ensure_ascii=False, indent=2
                )
            ),
        ]
    )

    return {
        "extracted_clauses": [
            {
                "chunk_id": chunk_id,
                "clause_id": f"{chunk_id}_{index+1}",
                "clause_type": clause.clause_type,
                "clause_text": clause.clause_text,
                "section_title": section_title,
                "source_text": section_text,
            }
            for index, clause in enumerate(extracted_clauses.clauses)
        ]
    }

def route_to_risk_detection(state: ToSAgentState):
    # Map over the extracted clauses produced by the previous parallel step
    return [
        Send("risk_detection", {"clause": clause})
        for clause in state["extracted_clauses"]
    ]

#-- - - - Agent 2: Risk Detection - - -
'''
## This agent does the core work of this project work i.e. legal reasoning.
## It analyzes the clauses extracted by the extractuon agent and find legal risks that a user might face.

## The llm call returns:
DetectedRisks:
level: RiskLevel        -> Low/Medium/High
risk_found: bool        -> True/False
confidence: int         -> How certain it is about the result it produced - 0% - 100%
category: RiskCategory  -> Category of Risk ex: Privacy, Liability, Payment, etc.
reason: str             -> Reason why this is a risk
evidence: str           -> text from the user input that contains this risk
'''

async def risk_detection_node(state: dict) -> ToSAgentState:
    clause_to_analyze = state["clause"]
    section_title = clause_to_analyze["section_title"]
    clause_text = clause_to_analyze["clause_text"]
    clause_type = clause_to_analyze["clause_type"]
    source_text = clause_to_analyze["source_text"]
    clause_id = clause_to_analyze["clause_id"]
    chunk_id = clause_to_analyze["chunk_id"]

    structured_llm = llm.with_structured_output(DetectedRisks)

    risk_detection_llm_input = {
        "section_title": section_title,
        "clause_type": clause_type,
        "clause_text": clause_text,
        "source_text": source_text,
    }

    detected_risk = await structured_llm.ainvoke(
        [
            SystemMessage(content=risk_detection_instruction),
            HumanMessage(
                content=json.dumps(
                    risk_detection_llm_input, ensure_ascii=False, indent=2
                )
            ),
        ]
    )

    if detected_risk.risk_found:
        return {
            "detected_risks": [
                {
                    "section_title": section_title,
                    "clause_id": clause_id,
                    "chunk_id": chunk_id,
                    "clause_text": clause_text,
                    "level": detected_risk.level,
                    "confidence": detected_risk.confidence,
                    "category": detected_risk.category,
                    "reason": detected_risk.reason,
                    "evidence": detected_risk.evidence,
                    "source_text": source_text,
                }
            ]
        }
    return {"detected_risks": []}

def route_to_explainer(state: ToSAgentState):
    # Fan out the risk analysis results into parallel explainer workers
    return [
        Send("explainer", {"detected_risk": detected_risk})
        for detected_risk in state["detected_risks"]
    ]

# - - - Agent 3: Explainer Agent (with Citations) - - -
'''
## This agent is the Explanation Agent.
## It does not have legal analysis capabilities.
## It explains legal clause in plain english so that an average user with no legal background can easily understand it.

## The llm call returns:
ExplainedRisk:
    whyMatters: str
    recommendation: str
'''
async def explanation_node(state: dict) -> ToSAgentState:
    detected_risk = state["detected_risk"]
    chunk_id = detected_risk["chunk_id"]
    clause_id = detected_risk["clause_id"]
    section_title = detected_risk["section_title"]

    structured_llm = llm.with_structured_output(ExplainedRisk)
    explainer_llm_input = {
        "category": detected_risk["category"],
        "reason": detected_risk["reason"],
        "evidence": detected_risk["evidence"],
    }

    structured_data = await structured_llm.ainvoke(
        [
            SystemMessage(content=explanation_instruction),
            HumanMessage(content=json.dumps(explainer_llm_input, indent=2)),
        ]
    )

    return {
        "explanations": [
            {
                "chunk_id": chunk_id,
                "clause_id": clause_id,
                "section_title": section_title,
                "category": detected_risk["category"],
                "level": detected_risk["level"],
                "confidence": detected_risk["confidence"],
                "reason": detected_risk["reason"],
                "whyMatters": structured_data.whyMatters,
                "recommendation": structured_data.recommendation,
                "evidence": detected_risk["evidence"],
                "source_text": detected_risk["source_text"],
            }
        ]
    }

# - - - Agent 4: Final Report Generator - - -
'''
## This is an agregator of explanation generated in the previous step.
## It combines all the explanations stored in the state and then maps it to a 'final_report' that satisfies the front-end contract.
'''
def report_generator_node(state: ToSAgentState) -> ToSAgentState:
    # Compiles and finalizes payload structure for the UI contract
    explanations = state["explanations"]
    formatted_risks = []
    for item in explanations:
        formatted_risks.append(
            {
                "chunk_id": item["chunk_id"],
                "clause_id": item["clause_id"],
                "section_title": item["section_title"],
                "level": item["level"],
                "confidence": item["confidence"],
                "category": item["category"],
                "reason": item["reason"],
                "whyMatters": item["whyMatters"],
                "recommendation": item["recommendation"],
                "exactClause": item["evidence"],
                "source_text": item["source_text"],
            }
        )
    return {"final_report": formatted_risks}


def build_tos_graph():
    '''
    ## The initial state of the graph is:
        initial_graph_state:
            "sections": chunks, <- Only this is populated initially
            "retrieved_chunks": []
            "extracted_clauses": []
            "detected_risks": []
            "plain_explanations": []
            "final_report": []

    ## Graph Start: The input of the graph is a 'list of chunks' created when the user input(text/docs/pdf) is parsed.
    ## Each chunk contains a 'section' from the user input.
    ## For each chunk one 'clause_extraction' node is invoked.
    ## Each 'clause_extraction' node returns its result to state["extracted_clauses"], later used by 'risk_detection' node.
    ## Each risk_detection node returns its result to state["detected_risks"], later used by the explainer node.
    ## Every explainer node add its explanation to the state["explanations"].
    ## The report_generator node uses the state["explanations"] and generates the final report and return to state["final_report"]
    '''

    builder = StateGraph(ToSAgentState)
    # Nodes
    builder.add_node("clause_extraction", clause_extraction_node)
    builder.add_node("risk_detection", risk_detection_node)
    builder.add_node("explainer", explanation_node)
    builder.add_node("report_generator", report_generator_node)

    # Edges
    builder.add_conditional_edges(
        START, route_to_clause_extraction, ["clause_extraction"]
    )
    builder.add_conditional_edges(
        "clause_extraction", route_to_risk_detection, ["risk_detection"]
    )
    builder.add_conditional_edges("risk_detection", route_to_explainer, ["explainer"])
    builder.add_edge("explainer", "report_generator")
    builder.add_edge("report_generator", END)

    return builder.compile()


## Keeeping it here for now to use with LangGraph Studio compilation for quick demo if the UI fails.
# graph = build_tos_graph()
