import os
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"

import asyncio
import json
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional
from app.services.file_parser import parse_and_chunk_file
from app.services.vector_store import store_chunks_in_db
from app.services.agent_pipeline import run_agent_pipeline


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
    tosText: Annotated[Optional[str], Form()] = None
    ):
    print("******** BACKEND CALL SUCCESSFUL *********")
    print(f"Received tosText: {tosText}")
    print(f"Received file: {file.filename if file else 'None'}")

    async def event_generator():
        try:
            # 1. Step: Document parsing and chunking
            yield json.dumps({"status": "processing", "message": "Starting document parsing and chunking..."}) + "\n"

            chunks = []
            if tosText and tosText:
                print("Processing raw text string...")
                chunks = await parse_and_chunk_file(tosText=tosText)
                totalChunks = store_chunks_in_db(chunks, "Pasted Text")
            elif file:
                print(f"Processing file: {file.filename}...")
                try:
                    chunks = await parse_and_chunk_file(file=file)
                    totalChunks = store_chunks_in_db(chunks, file.filename)
                    print(f"Successfully generated and stored {totalChunks} chunks in vector db.")
                except Exception as e:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Processing Error | Something went wrong: {str(e)}"
                    )
            else:
                yield json.dumps({"status": "error", "message": "No text or file provided."}) + "\n"
                return

            yield json.dumps({"status": "processing", "message": "Executing legal risk analysis agent pipeline..."}) + "\n"
            final_report = await run_agent_pipeline(chunks)
            print("* * * * * final_report * * * * *")
            print(final_report)

            final_report_data = final_report.get("report", [])
            yield json.dumps({
                "status": "success",
                "message": "Analysis complete!",
                "report": final_report_data  # This should evaluate to your list of risk objects
            }) + "\n"
        except Exception as e:
            print(f"Error during pipeline execution: {str(e)}")
            yield json.dumps({
                "status": "error", 
                "message": f"Processing Error | Something went wrong: {str(e)}"
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")