import os

os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"

import json
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional
from app.services.file_parser import parse_and_chunk_file
from app.services.vector_store import store_chunks_in_db
from app.agent.tos_graph import build_tos_graph
from app.agent.tos_agent_states import initial_graph_state

app = FastAPI(title="Terms Of Service Risk Analyzer")

# Whitelisting local UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # change if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze-document")
async def parse_document(
    file: Annotated[Optional[UploadFile], File()] = None,
    tosText: Annotated[Optional[str], Form()] = None,
):
    print("******** BACKEND CALL SUCCESSFUL *********")
    print(f"Received tosText: {tosText}")
    print(f"Received file: {file.filename if file else 'None'}")

    async def event_generator():
        try:
            ##############
            # DUMMY ERROR FOR TESTING
            # error = {
            #          'message': f'Processing Error | Something went wrong',
            #          'error': "API ERROR TEST"  # Sends "ValueError", "KeyError", etc., safely
            # }
            # yield f"data: {json.dumps({'type': 'error', 'message': f'Error: Something went wrong', 'error': error})}\n\n"
            # return
            ##############
            
            yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Starting document parsing and chunking...'})}\n\n"

            chunks = []
            if tosText and tosText:
                # print("Processing raw text string...")
                yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Processing your text.'})}\n\n"
                chunks = await parse_and_chunk_file(tosText=tosText)
                ### totalChunks = store_chunks_in_db(chunks, "Pasted Text")
                ### print(f"Successfully generated and stored {totalChunks} chunks in vector db.")
            elif file:
                yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Processing your file.'})}\n\n"
                # print(f"Processing file: {file.filename}...")
                try:
                    chunks = await parse_and_chunk_file(file=file)
                    ### totalChunks = store_chunks_in_db(chunks, file.filename)
                    ### print(f"Successfully generated and stored {totalChunks} chunks in vector db.")
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'status', 'status': 'error', 'message': str(e)})}\n\n"
                    raise HTTPException(
                        status_code=500,
                        detail=f"Processing Error | Something went wrong: {str(e)}",
                    )
            else:
                yield f"data: {json.dumps({'type': 'status', 'status': 'error', 'message': 'No text or file provided.'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Executing legal risk analysis agent pipeline.'})}\n\n"

            final_report_data = []
            graph = build_tos_graph()
            initial_state = initial_graph_state
            initial_state["sections"] = chunks

            async for event in graph.astream(initial_state, stream_mode="updates", config={'max_concurrency': 2}):
                for node_name, node_output in event.items():
                    if node_name == "clause_extraction":
                        yield f"data: {json.dumps({'type': 'status', "status": "processing", "message": "Extracting clauses..."})}\n\n"
                    elif node_name == "risk_detection":
                        yield f"data: {json.dumps({'type': 'status', "status": "processing", "message": "Analyzing Risks..."})}\n\n"
                    elif node_name == "explainer":
                        yield f"data: {json.dumps({'type': 'status', "status": "processing", "message": "Generating explanations..."})}\n\n"
                    elif node_name == "report_generator":
                        yield f"data: {json.dumps({'type': 'status', "status": "processing", "message": "Preparing Report..."})}\n\n"
                        final_report_data = node_output.get("final_report", [])

            # Stream each risk item individually to match front end contract
            if not final_report_data:
                print(' * * * * * * * * * * NO RISK FOUND * * * * * * * * * *')
                yield f"data: {json.dumps({'type': 'no_risks_found', 'content': None})}\n"
            else:
                for risk in final_report_data:
                    print(' * * * * * * * * * * FINAL REPORT * * * * * * * * * *')
                    yield f"data: {json.dumps({'type': 'risk_item', 'content': risk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_payload = {
                'message': f'Processing Error | Something went wrong: {str(e)}',
                'error': type(e).__name__  #"ValueError", "KeyError", etc., safely
            }
            yield f"data: {json.dumps({'type': 'error', 'message': f'Processing Error | Something went wrong: {str(e)}', 'error': 
            error_payload})}\n\n"
            return
            

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
