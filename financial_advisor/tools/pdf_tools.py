import io
import re
from pathlib import Path

import fitz  # PyMuPDF
from google.adk.tools import ToolContext


def extract_text_from_pdf(file_path: str, tool_context: ToolContext = None) -> dict:
    """
    Extracts all readable text from a PDF file, preserving page structure.

    Supports two modes:
    - ADK artifact: file uploaded via the ADK web UI (tool_context injected automatically)
    - Local path: absolute or relative path string provided by the user

    Args:
        file_path (str): Artifact filename or local path to the PDF.
        tool_context (ToolContext): Injected by ADK; used to load uploaded artifacts.

    Returns:
        dict: status, total_pages, full_text, and pages preview or error.
    """
    try:
        import fitz
    except ImportError:
        return {"status": "error", "error": "PyMuPDF not installed. Run: pip install pymupdf"}

    doc = None
    file_name = Path(file_path).name

    # Load from ADK artifact when a file is uploaded via the ADK web UI
    if tool_context is not None:
        try:
            artifact = tool_context.load_artifact(file_path)
            if artifact and hasattr(artifact, "inline_data") and artifact.inline_data:
                pdf_bytes = artifact.inline_data.data
                doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
        except Exception:
            pass

    # Fall back to reading from a local file path
    if doc is None:
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "error": f"File not found: {file_path}"}
        if path.suffix.lower() != ".pdf":
            return {"status": "error", "error": "File must be a .pdf"}
        doc = fitz.open(str(path))
        file_name = path.name

    try:
        pages_text = []
        full_text = ""

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            pages_text.append({"page": page_num, "content": text.strip()})
            full_text += f"\n--- PAGE {page_num} ---\n{text}"

        doc.close()

        if not full_text.strip():
            return {"status": "error", "error": "No readable text found. PDF may be scanned/image-based."}

        return {
            "status": "success",
            "file_name": file_name,
            "total_pages": len(pages_text),
            "full_text": full_text[:15000],
            "pages": pages_text[:5],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def detect_financial_document_type(text_snippet: str) -> dict:
    """
    Detects the type of financial document from a text snippet.

    Args:
        text_snippet (str): First 2000 characters of extracted PDF text.

    Returns:
        dict: status, document_type, and confidence level.
    """
    text_lower = text_snippet.lower()

    INDICATORS = {
        "balance_sheet":        ["total assets", "total liabilities", "shareholders equity", "current assets"],
        "income_statement":     ["revenue", "gross profit", "net income", "earnings per share", "profit and loss"],
        "cash_flow_statement":  ["cash flow", "operating activities", "investing activities", "financing activities"],
        "annual_report":        ["annual report", "chairman", "board of directors", "financial highlights"],
        "bank_statement":       ["account number", "transaction date", "debit", "credit", "closing balance"],
        "invoice":              ["invoice number", "due date", "bill to", "total amount due"],
        "payslip":              ["basic salary", "epf", "socso", "gross pay", "net pay"],
        "audit_report":         ["independent auditor", "audit opinion", "material misstatement"],
    }

    scores: dict[str, int] = {}
    for doc_type, keywords in INDICATORS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[doc_type] = score

    if not scores:
        return {"status": "success", "document_type": "unknown", "confidence": "low"}

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"

    return {
        "status": "success",
        "document_type": best_type,
        "confidence": confidence,
        "match_score": f"{best_score}/{len(INDICATORS[best_type])}",
    }


def extract_key_financial_figures(text: str) -> dict:
    """
    Scans financial document text for key monetary figures and labels.

    Args:
        text (str): Full extracted text from the financial PDF.

    Returns:
        dict: status and list of extracted figures with labels and amounts.
    """
    CURRENCY_PATTERN = re.compile(
        r"([A-Za-z &]+?)\s*[:\-]?\s*(RM|MYR|USD|\$|€|£)\s*([\d,]+(?:\.\d{1,2})?)",
        re.IGNORECASE,
    )
    LABEL_NUMBER_PATTERN = re.compile(
        r"(total [a-z ]+|net income|gross profit|revenue|earnings|profit|loss|equity|liabilities|assets|cash)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
        re.IGNORECASE,
    )

    figures = []
    seen_labels = set()

    for match in CURRENCY_PATTERN.finditer(text):
        label = match.group(1).strip()
        currency = match.group(2)
        amount_str = match.group(3).replace(",", "")
        if label and label.lower() not in seen_labels:
            try:
                figures.append({"label": label, "currency": currency, "amount": float(amount_str)})
                seen_labels.add(label.lower())
            except ValueError:
                continue

    for match in LABEL_NUMBER_PATTERN.finditer(text):
        label = match.group(1).strip()
        amount_str = match.group(2).replace(",", "")
        if label and label.lower() not in seen_labels:
            try:
                figures.append({"label": label, "currency": "N/A", "amount": float(amount_str)})
                seen_labels.add(label.lower())
            except ValueError:
                continue

    return {
        "status": "success",
        "figures_count": len(figures),
        "key_figures": figures[:20],
    }