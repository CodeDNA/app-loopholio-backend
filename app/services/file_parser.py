import os, tempfile
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from fastapi import HTTPException
import io


async def parse_and_chunk_file(file=None, tosText: str = "") -> list[dict]:
    converter = DocumentConverter()
    tmp_path = None
    chunks = []

    try:
        if not file:
            # Create a temp file to store the pasted text string
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".txt", mode="w", encoding="utf-8"
            ) as tmp:
                tmp.write(tosText)
                tmp_path = tmp.name
            target_path = tmp_path
        else:
            suffix = os.path.splitext(file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                contents = await file.read()
                tmp.write(contents)
                tmp_path = tmp.name
            target_path = tmp_path
        conv_result = converter.convert(target_path)
        doc = conv_result.document
        # extracted_text = doc.export_to_markdown()
        chunker = HybridChunker()
        chunk_iter = chunker.chunk(dl_doc=doc)

        for index, chunk in enumerate(chunk_iter):

            headings = (
                getattr(chunk.meta, "headings", []) if hasattr(chunk, "meta") else []
            )
            section_title = headings[0] if headings else "User pasted text"
            chunk_id = f"chunk_00{index}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "section_title": section_title,
                    "section_text": chunk.text,
                    # "section_context": chunker.contextualize(chunk),
                    "metadata": chunk.meta,
                }
            )
        return chunks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docling parsing error: {str(e)}")
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
