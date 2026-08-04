from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
from app.agent.tos_agent_states import ToSAgentState, RiskReportItem
from langgraph.types import Send
from app.llm.llm_factory import get_llm
from app.agent.all_instructions import clause_extraction_instruction, risk_detection_instruction, explanation_instruction

llm = get_llm()

def route_to_clause_extraction(state: ToSAgentState):
    return [Send("clause_extraction", {"section": sec}) for sec in state["sections"]]

# --- Agent 1: Clause Extraction ---
async def clause_extraction_node(state: dict) -> ToSAgentState:
    section = state["section"]
    section_title = section.get("title", "General")
    section_context = section.get("context", "")

    systemMessage = clause_extraction_instruction.format(title=section_title, context=section_context)
    extracted_clause = await llm.ainvoke([SystemMessage(content=systemMessage)])
    
    return {
        "extracted_clauses": [{
            "title": section_title,
            "clause": extracted_clause.content
        }]
    }

def route_to_risk_detection(state: ToSAgentState):
    # Map over the extracted clauses produced by the previous parallel step
    return [Send("risk_detection", {"clause": clause}) for clause in state["extracted_clauses"]]

# --- Agent 2: Risk Detection ---
async def risk_detection_node(state: dict) -> ToSAgentState:
    extracted_clause = state["clause"]
    clause_title = extracted_clause.get("title", "General")
    clause_content = extracted_clause.get("clause", "")

    systemMessage = risk_detection_instruction.format(title=clause_title,context=clause_content)
    detected_risk = await llm.ainvoke([SystemMessage(content=systemMessage)])
    return {
        "risk_analysis": [{
            "title": clause_title,
            "clause": clause_content,
            "risk_assessment": detected_risk.content
        }]
    }

def route_to_explainer(state: ToSAgentState):
    # Fan out the risk analysis results into parallel explainer workers
    return [Send("explainer", {"detected_risk": detected_risk}) for detected_risk in state["risk_analysis"]]

# --- Agent 3: Explainer Agent (with Citations) ---
async def explanation_node(state: dict) -> ToSAgentState:
    risk_analysis = state.get("detected_risk", [])
    risk_title = risk_analysis.get("title", "General")
    risk_assessment = risk_analysis.get("risk_assessment", "")
    
    # Enforce the strict UI schema contract at this translation step
    structured_llm = llm.with_structured_output(RiskReportItem)
    
    system_message = explanation_instruction.format(
        title=risk_title,
        risk_assessment=risk_assessment
    )
    structured_data = await structured_llm.ainvoke([SystemMessage(content=system_message)])

    return {
        "explanations": [{
            "title": risk_title,
            "data": structured_data
        }]
    }

'''
# # --- Agent 2 & 3: Combined Risk Detection & Explainer using Structured Output ---
def risk_and_explanation_node(state: ToSAgentState) -> ToSAgentState:
    clauses = state.get("extracted_clauses", [])
    combined_clauses = "\n\n".join([c["clause_text"] for c in clauses])
    
    # Force the LLM to output an array matching your exact UI schema
    structured_llm = llm.with_structured_output(List[RiskReportItem])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a legal risk assessment agent. Analyze the provided clauses, assess their risk, translate legalese into plain English explanations, and provide actionable recommendations."),
        ("human", "Extracted Clauses:\n{clauses}")
    ])
    
    chain = prompt | structured_llm
    report_items = chain.invoke({"clauses": combined_clauses})
    
    # Convert Pydantic models back to dictionaries for the state graph
    serialized_report = [item.model_dump() for item in report_items]
    
    state["risk_analysis"] = serialized_report
    state["plain_explanations"] = serialized_report
    return state
'''

# --- Agent 4: Final Report Generator ---
def report_generator_node(state: ToSAgentState) -> ToSAgentState:
    # Compiles and finalizes payload structure for the UI contract
    explanations = state.get("explanations", [])
    formatted_risks = []
    for item in explanations:
        # If your explanations are nested (e.g., inside an "explanations" sub-key), 
        # extract the actual data dict here. Assuming 'item' is the flat dictionary:
        formatted_risks.append({
            "level": item["data"].get("level", "Uncategorized"),
            "confidence": item["data"].get("confidence", 0),
            "category": item["data"].get("category", "Uncategorized"),
            "reason": item["data"].get("reason", "No reason provided."),
            "whyMatters": item["data"].get("whyMatters", "No explanation available."),
            "recommendation": item["data"].get("recommendation", "Review this clause carefully."),
            "exactClause": item["data"].get("exactClause", "Clause text unavailable.")
        })
    return {"final_report": formatted_risks}

def build_tos_graph():
    builder = StateGraph(ToSAgentState)
    
    # Nodes
    builder.add_node("clause_extraction", clause_extraction_node)
    builder.add_node("risk_detection", risk_detection_node)
    builder.add_node("explainer", explanation_node)
    builder.add_node("report_generator", report_generator_node)

    # Edges
    builder.add_conditional_edges(START, route_to_clause_extraction,["clause_extraction"])
    builder.add_conditional_edges("clause_extraction", route_to_risk_detection,["risk_detection"])
    builder.add_conditional_edges("risk_detection", route_to_explainer,["explainer"])
    builder.add_edge("explainer", "report_generator")
    builder.add_edge("report_generator", END)
    
    return builder.compile()

tos_graph = build_tos_graph()