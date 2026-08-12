import os
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"

import json
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional
from app.services.file_parser import parse_and_chunk_file
### from app.services.vector_store import store_chunks_in_db
from app.agent.tos_graph import build_tos_graph
from app.agent.tos_agent_states import initial_graph_state
from app.services.rate_limiter import remove_analysis_lock, can_process
from app.constants.constants import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_ERROR, MIN_REQUIRED_TEXT_LENGTH, MIN_REQUIRED_TEXT_LENGTH_ERROR, MAX_ALLOWED_TEXT_LENGTH, MAX_ALLOWED_TEXT_LENGTH_ERROR, MAX_SECTIONS_ALLOWED_PER_DOCUMENT

app = FastAPI(title="Terms Of Service Risk Analyzer")

# Whitelisting local UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://loopholio.codedna.io"
        ],  # change if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

'''
API for health monitoring
'''
@app.get("/health")
async def health_check():
    return {"status": "ok"}

'''
Api to analyze document. It parses the document and performs chunking.
The chunks are then send to the agent graph for risk analysis.

Input
It can take either a document file or a text.

Output:
It retuns a list of dictionary - list of potential risk items present in the legal document.
'''
@app.post("/analyze-document")
async def parse_document(
    file: Annotated[Optional[UploadFile], File()] = None,
    tosText: Annotated[Optional[str], Form()] = None,
    request: Request = None,
):
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
            # result = can_process(request)
            # if not result["allow"]:
            #     error_payload = {
            #                     'message': f'{result['message']}. Please try again after some time.',
            #                     'error': "API Rate Limit - Too Many Requests."
            #     }
            #     yield f"data: {json.dumps({'type': 'error', 'message': 'Too many requests. Please try again after some time.', 'error': error_payload})}\n\n"
            #     return
            
            # yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Parsing document...'})}\n\n"

            chunks = []
            if tosText and tosText:
                # print("Processing raw text string...")
                if len(tosText) < MIN_REQUIRED_TEXT_LENGTH:
                    error_payload = {
                                    'message': MIN_REQUIRED_TEXT_LENGTH_ERROR,
                                    'error': "Input text requirement - min length"
                    }
                    yield f"data: {json.dumps({'type': 'error', 'message': MIN_REQUIRED_TEXT_LENGTH_ERROR, 'error': error_payload})}\n\n"
                    return

                if len(tosText) > MAX_ALLOWED_TEXT_LENGTH:
                    error_payload = {
                                    'message': MAX_ALLOWED_TEXT_LENGTH_ERROR,
                                    'error': f'Max input length exceeded: ({len(tosText)})'
                    }
                    yield f"data: {json.dumps({'type': 'error', 'message': MAX_ALLOWED_TEXT_LENGTH_ERROR, 'error': error_payload})}\n\n"
                    return

                result = can_process(request)
                if not result["allow"]:
                    error_payload = {
                                    'message': f'{result['message']}. Please try again after some time.',
                                    'error': "API Rate Limit - Too Many Requests."
                    }
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Too many requests. Please try again after some time.', 'error': error_payload})}\n\n"
                    return
                yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Processing your text.'})}\n\n"
                chunks = await parse_and_chunk_file(tosText=tosText)
                if len(chunks) > MAX_SECTIONS_ALLOWED_PER_DOCUMENT:
                    error_payload = {
                                    'message': f'Too many sections present in the provided document. Max sections allowed per document: {MAX_SECTIONS_ALLOWED_PER_DOCUMENT}',
                                    'error': f"Too many sections in the document ({len(chunks)})"
                    }
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Processing Error | Too many sections/pages in the document. Max sections allowed per document: {MAX_SECTIONS_ALLOWED_PER_DOCUMENT}', 'error': error_payload})}\n\n"
                    return
                ### totalChunks = store_chunks_in_db(chunks, "Pasted Text")
                ### print(f"Successfully generated and stored {totalChunks} chunks in vector db.")
            elif file:
                if file.size is None or file.size > MAX_FILE_SIZE_BYTES:
                    error_payload = {
                                'message': f'{MAX_FILE_SIZE_ERROR}',
                                'error': "Processing Error | Max file size exceeded"
                    }
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Processing Error | {MAX_FILE_SIZE_ERROR}', 'error': error_payload})}\n\n"
                    return
                result = can_process(request)
                if not result["allow"]:
                    error_payload = {
                                    'message': f'{result['message']}. Please try again after some time.',
                                    'error': "API Rate Limit - Too Many Requests."
                    }
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Too many requests. Please try again after some time.', 'error': error_payload})}\n\n"
                    return

                yield f"data: {json.dumps({'type': 'status', 'status': 'processing', 'message': 'Processing your file.'})}\n\n"
                try:
                    chunks = await parse_and_chunk_file(file=file)
                    if len(chunks) > MAX_SECTIONS_ALLOWED_PER_DOCUMENT:
                        error_payload = {
                                        'message': f'Too many sections present in the provided document. Max sections allowed per document: {MAX_SECTIONS_ALLOWED_PER_DOCUMENT}',
                                        'error': f"Too many sections in the document ({len(chunks)})"
                        }
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Processing Error | Too many sections/pages in the document. Max sections allowed per document: {MAX_SECTIONS_ALLOWED_PER_DOCUMENT}', 'error': error_payload})}\n\n"
                        return
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
                print(' * * * * * * * * * * FINAL REPORT * * * * * * * * * *')
                count = 0
                for risk in final_report_data:
                    count += 1
                    yield f"data: {json.dumps({'type': 'risk_item', 'content': risk})}\n\n"
                print(f' * * * * * * * * * * TOTAL RISKS FOUND: {count}* * * * * * * * * *')

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_payload = {
                'message': f'Processing Error | Something went wrong: {str(e)}',
                'error': type(e).__name__  #"ValueError", "KeyError", etc., safely
            }
            yield f"data: {json.dumps({'type': 'error', 'message': f'Processing Error | Something went wrong: {str(e)}', 'error': 
            error_payload})}\n\n"
            return
        finally:
            # Remove analysis lock when current analysis finishes or an exception is caught
            remove_analysis_lock(request)
            

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
