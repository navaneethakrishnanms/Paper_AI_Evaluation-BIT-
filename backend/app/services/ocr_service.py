"""
OCR Service using LLM (Llama 4 Maverick via Groq API).
Converts PDF pages to images and uses the LLM for text extraction.
"""
import fitz  # PyMuPDF
import base64
import io
from pathlib import Path
from typing import List


def pdf_to_base64_images(pdf_path: str, dpi: int = 200) -> List[str]:
    """
    Convert PDF pages to base64-encoded PNG images.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for rendering PDF pages
    
    Returns:
        List of base64-encoded image strings
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    images = []
    doc = fitz.open(str(pdf_path))
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to image at specified DPI
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            
            # Encode as base64
            b64_string = base64.standard_b64encode(img_bytes).decode("utf-8")
            images.append(b64_string)
    
    finally:
        doc.close()
    
    return images


def get_extraction_prompt(is_handwritten: bool = False) -> str:
    """
    Get the system prompt for text extraction.
    """
    if is_handwritten:
        return """You are an expert OCR system specialized in reading handwritten text.
Extract ALL text from this image exactly as written. 
- Preserve the original structure (headings, paragraphs, numbered lists)
- Include question numbers like A1, B2, (i), (ii), etc.
- If text is unclear, make your best guess based on context
- Do NOT add any commentary or explanation
- Output ONLY the extracted text"""
    else:
        return """You are an expert OCR system.
Extract ALL text from this image exactly as written.
- Preserve the original structure (headings, sections, numbering)
- Include all question numbers, marks allocation, and instructions
- Do NOT add any commentary or explanation  
- Output ONLY the extracted text"""
