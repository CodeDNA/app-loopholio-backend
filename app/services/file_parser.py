import os, tempfile
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from fastapi import HTTPException
import re, httpx
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter

'''
## This creates chunks from the document provided by the user and saves it to the vector database -currently using ChromaDB.
## This uses HybridChunker() from the IBM's docling API.
## HybridChunker() chunks the document based on headings and paragraphs. I chose this so that maximum context is preserved in the chunks and the text is not sliced mid sentence.

### Types of input curretly supported:
- document: pdf, txt, docx
- image: png, jpg, jpeg, tiff
'''
async def parse_and_chunk_file(file=None, tosText: str = "", isURl: str = 'false') -> list[dict]:
    print("isURl type: ", type(isURl))
    converter = DocumentConverter()
    tmp_path = None
    chunks = []

    try:
        if isURl == "true":
            target_path = tosText
        elif not file:
            # Create a temp file to store the pasted text string
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".txt", mode="w", encoding="utf-8"
            ) as tmp:
                tmp.write(tosText)
                tmp_path = tmp.name
            target_path = tmp_path
        else:
            suffix = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                contents = await file.read()
                tmp.write(contents)
                tmp_path = tmp.name
            target_path = tmp_path
        conv_result = converter.convert(target_path)
        if isURl == "true" and len(conv_result.document.texts) <= 1:
            await convert_url(tosText)
        doc = conv_result.document
        chunker = HybridChunker()
        chunk_iter = chunker.chunk(dl_doc=doc)

        for index, chunk in enumerate(chunk_iter):
            headings = (
                getattr(chunk.meta, "headings", []) if hasattr(chunk, "meta") else []
            )
            if skip_chunk(headings, chunk.text):
                continue
            section_title = headings[0] if headings else ""
            chunk_id = f"chunk_00{index}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "section_title": section_title,
                    "section_text": chunk.text,
                    "section_context": chunker.contextualize(chunk),
                    "metadata": chunk.meta,
                }
            )
        return chunks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docling parsing error: {str(e)}")
    finally:
        if (not isURl == "true") and "tmp_path" in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

def is_navigation_chunk(text: str) -> bool:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return True

    markdown_link_lines = sum(
        bool(re.search(r"\[[^\]]+\]\([^)]+\)", line))
        for line in lines
    )
    return markdown_link_lines / len(lines) > 0.7

def is_document_metadata(
    text: str,
    headings: list[str] | None = None,
) -> bool:
    normalized = " ".join(text.lower().split())
    headings = headings or []

    metadata_patterns = [
        r"\beffective date\b",
        r"\beffective\s+[a-z]+\s+\d{1,2},\s+\d{4}\b",
        r"\blast updated\b",
        r"\blast revised\b",
        r"\barchived versions?\b",
        r"\bprevious versions?\b",
        r"\bdownload pdf\b",
        r"\bcountry version\b",
    ]

    legal_signals = [
        "you agree",
        "you must",
        "you may",
        "we may",
        "we reserve",
        "shall",
        "liable",
        "liability",
        "terminate",
        "indemnif",
        "warranty",
        "refund",
        "arbitration",
        "governing law",
    ]

    metadata_score = sum(
        bool(re.search(pattern, normalized))
        for pattern in metadata_patterns
    )

    has_legal_signal = any(
        signal in normalized
        for signal in legal_signals
    )

    return metadata_score >= 2 and not has_legal_signal

def skip_chunk(headings, text) -> bool:
    normalized_headings = []
    if headings:
         normalized_headings = {h.lower().strip() for h in headings}
    if not text:
        return True
    if normalized_headings and "contents" in normalized_headings:
        return True
    if normalized_headings and "definitions" in normalized_headings:
        return True
    if is_navigation_chunk(text):
         return True
    if is_document_metadata(text):
         return True
    
async def convert_url(url: str):
    headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15.0,
    ) as client:
        response = await client.get(
            url,
            headers=headers,
        )

        response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()

    print("*********:", response.status_code)
    print("STATUS:", response.status_code)
    print("FINAL URL:", response.url)
    print("CONTENT TYPE:", content_type)
    print("RESPONSE SIZE:", len(response.content))

    if "text/html" in content_type:
        html = response.text.lower()

        for phrase in [
            "terms of service",
            "liability",
            "indemnif",
            "privacy",
        ]:
            print(phrase, phrase in html)
            return
        ########## 
        result = DocumentConverter().convert_string(
            response.text,
            format=InputFormat.HTML,
            name=str(response.url),
        )

        return result.document

    raise ValueError(
        f"Unsupported URL content type: {content_type}"
    )