from fastapi import HTTPException
from app.agent.tos_graph import tos_graph

async def run_agent_pipeline(chunks: list[dict]):
    print("Running : run_agent_pipeline")

    combined_text = "\n".join([chunk.get("text", "") for chunk in chunks])

    try:
        # Initial state setup for LangGraph
        initial_state = {
            "sections": chunks, # TODO: Create Sections class, chunks go as list of sections
            # "retrieved_chunks": [],
            "extracted_clauses": [],
            "risk_analysis": [],
            "plain_explanations": [],
            "final_report": []
        }
        # Run the compiled graph asynchronously
        result = await tos_graph.ainvoke(initial_state)
        
        return {
            "status": "success",
            "report": result.get("final_report", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")