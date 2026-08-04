from app.agent.instructions.clause_extraction_instruction import clause_extraction_instruction
from app.agent.instructions.final_report_generator_instruction import final_report_generator_instruction
from app.agent.instructions.risk_detection_instruction import risk_detection_instruction
from app.agent.instructions.explanation_instruction import explanation_instruction

clause_extraction_instruction = clause_extraction_instruction

risk_detection_instruction = risk_detection_instruction

explanation_instruction = explanation_instruction

final_report_generator_instruction = final_report_generator_instruction


# prompt = ChatPromptTemplate.from_messages([
    #     ("system", "You are an explainer agent. Translate the technical risk assessments and legalese into plain English explanations, provide recommendations, and extract exact verbatim clauses."),
    #     ("human", "Risk Analysis Findings:\n{risk_data}")
    # ])