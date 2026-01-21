"""
LLM Evaluator Service - Holistic Pipeline Orchestrator
PT-II ONLY - Bannari Amman Institute of Technology

NEW 3-STAGE HOLISTIC PIPELINE:
1. OCR extraction (page by page)
2. Holistic evaluation (SINGLE LLM call with full context)
3. Final aggregation (no LLM)

Philosophy: "Understand first, evaluate holistically, then structure."

Key features:
- Single LLM call for all evaluation (vs 5+ before)
- Human-like evaluation by meaning, not labels
- Intelligent OCR error handling
- Checkpointing for resume capability
- Token budget enforcement
"""
import os
import json
import asyncio
import httpx
import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from .ocr_service import pdf_to_base64_images, get_extraction_prompt
from .checkpoint_service import CheckpointService
from .exam_checkpoint_service import ExamCheckpointService, generate_exam_id
from .job_store import job_store


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Resolve environment variables for all LLM configs
    def resolve_api_key(llm_config: Dict[str, Any]) -> None:
        api_key = llm_config.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            llm_config["api_key"] = os.getenv(env_var, "")
    
    # Resolve for legacy llm config
    if "llm" in config:
        resolve_api_key(config["llm"])
    
    # Resolve for OCR LLM (Maverick)
    if "ocr_llm" in config:
        resolve_api_key(config["ocr_llm"])
    
    # Resolve for Evaluation LLM (Qwen3-VL)
    if "evaluation_llm" in config:
        resolve_api_key(config["evaluation_llm"])
    
    return config


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response.
    Handles thinking models that include reasoning before/after JSON.
    """
    # First, try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                cleaned = match.strip()
                if cleaned.startswith('{'):
                    return json.loads(cleaned)
            except json.JSONDecodeError:
                continue
    
    # Try to find a JSON object by looking for { and matching }
    # Find all { positions and try to parse from each one
    brace_positions = [i for i, c in enumerate(text) if c == '{']
    
    for start in brace_positions:
        # Find matching closing brace by counting braces
        depth = 0
        end = start
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        if end > start:
            potential_json = text[start:end+1]
            try:
                return json.loads(potential_json)
            except json.JSONDecodeError:
                # Try cleaning common issues
                cleaned = potential_json
                # Remove trailing commas before closing braces/brackets
                cleaned = re.sub(r',\s*}', '}', cleaned)
                cleaned = re.sub(r',\s*]', ']', cleaned)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
    
    # Last resort: find first { and last } 
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        potential_json = text[start:end+1]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            # Try cleaning
            cleaned = potential_json
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
    
    raise ValueError("Could not extract valid JSON from LLM response")


def estimate_tokens(text: str) -> int:
    """Conservative token estimation (1 token ≈ 3 characters)."""
    return len(text) // 3


def truncate_for_holistic(text: str, max_chars: int = 5000) -> str:
    """
    Truncate text intelligently for holistic evaluation.
    Keeps beginning and end, removes middle if needed.
    """
    if len(text) <= max_chars:
        return text
    
    # Keep first 60% and last 40% for better context
    first_part = int(max_chars * 0.6)
    last_part = max_chars - first_part
    
    return text[:first_part] + "\n\n[...middle section truncated...]\n\n" + text[-last_part:]


async def call_groq_api(
    messages: List[Dict],
    config: Dict[str, Any],
    max_tokens: int = 3000
) -> str:
    """
    Call Groq API (Maverick) for OCR extraction.
    On 429/413, waits and retries - NEVER rebuilds prompt.
    """
    # Prefer ocr_llm config for OCR, fallback to llm
    llm_config = config.get("ocr_llm", config.get("llm", {}))
    base_url = llm_config.get("base_url", "https://api.groq.com/openai/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "meta-llama/llama-4-maverick-17b-128e-instruct")
    timeout = llm_config.get("timeout_seconds", 120)
    max_retries = llm_config.get("max_retries", 15)
    base_delay = llm_config.get("retry_backoff_seconds", 5)
    
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    
    # Log token estimation
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    est_tokens = estimate_tokens(str(total_chars))
    print(f"    [TOKEN EST] ~{est_tokens} tokens (input chars: {total_chars})")
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                print(f"    [API] Attempt {attempt + 1}/{max_retries}...")
                
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                
                elif response.status_code in [429, 413]:
                    retry_after = response.headers.get("retry-after")
                    if retry_after:
                        delay = int(retry_after) + 2
                    else:
                        delay = base_delay * (2 ** min(attempt, 4))
                    
                    error_type = "TPM/RPM limit" if response.status_code == 429 else "Request size limit"
                    print(f"    [RATE LIMIT] {error_type}. Waiting {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                elif response.status_code == 503:
                    delay = base_delay * (2 ** min(attempt, 3))
                    print(f"    [SERVICE] Unavailable. Waiting {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                else:
                    raise Exception(f"Groq API error {response.status_code}: {response.text}")
            
            except httpx.TimeoutException:
                delay = base_delay * (2 ** min(attempt, 3))
                print(f"    [TIMEOUT] Waiting {delay}s...")
                await asyncio.sleep(delay)
            
            except httpx.ConnectError:
                delay = base_delay * (2 ** min(attempt, 3))
                print(f"    [CONNECTION] Waiting {delay}s...")
                await asyncio.sleep(delay)
    
    raise Exception("Max retries exceeded")


async def call_fireworks_api(
    messages: List[Dict],
    config: Dict[str, Any],
    max_tokens: int = 32768
) -> str:
    """
    Call Fireworks AI API with Qwen3-VL for evaluation.
    Uses the thinking model for better reasoning.
    """
    llm_config = config.get("evaluation_llm", config.get("llm", {}))
    base_url = llm_config.get("base_url", "https://api.fireworks.ai/inference/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "accounts/fireworks/models/qwen3-vl-235b-a22b-thinking")
    timeout = llm_config.get("timeout_seconds", 300)
    max_retries = llm_config.get("max_retries", 10)
    base_delay = llm_config.get("retry_backoff_seconds", 5)
    temperature = llm_config.get("temperature", 0.6)
    top_p = llm_config.get("top_p", 1)
    top_k = llm_config.get("top_k", 40)
    
    if not api_key:
        raise ValueError("FIREWORKS_API_KEY not set")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "top_k": top_k,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "temperature": temperature,
        "messages": messages
    }
    
    # Log token estimation
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    est_tokens = estimate_tokens(str(total_chars))
    print(f"    [FIREWORKS] ~{est_tokens} est. tokens (input chars: {total_chars})")
    print(f"    [FIREWORKS] Using model: {model}")
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                print(f"    [FIREWORKS API] Attempt {attempt + 1}/{max_retries}...")
                
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    # Log usage if available
                    if "usage" in data:
                        usage = data["usage"]
                        print(f"    [FIREWORKS] Tokens used: {usage.get('total_tokens', 'N/A')}")
                    return content
                
                elif response.status_code in [429, 413]:
                    retry_after = response.headers.get("retry-after")
                    if retry_after:
                        delay = int(retry_after) + 2
                    else:
                        delay = base_delay * (2 ** min(attempt, 4))
                    
                    error_type = "Rate limit" if response.status_code == 429 else "Request size limit"
                    print(f"    [FIREWORKS RATE LIMIT] {error_type}. Waiting {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                elif response.status_code == 503:
                    delay = base_delay * (2 ** min(attempt, 3))
                    print(f"    [FIREWORKS SERVICE] Unavailable. Waiting {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                else:
                    print(f"    [FIREWORKS ERROR] Status {response.status_code}: {response.text[:500]}")
                    raise Exception(f"Fireworks API error {response.status_code}: {response.text}")
            
            except httpx.TimeoutException:
                delay = base_delay * (2 ** min(attempt, 3))
                print(f"    [FIREWORKS TIMEOUT] Waiting {delay}s...")
                await asyncio.sleep(delay)
            
            except httpx.ConnectError:
                delay = base_delay * (2 ** min(attempt, 3))
                print(f"    [FIREWORKS CONNECTION] Waiting {delay}s...")
                await asyncio.sleep(delay)
    
    raise Exception("Fireworks API: Max retries exceeded")


async def extract_text_with_llm(
    pdf_path: str,
    config: Dict[str, Any],
    is_handwritten: bool = False
) -> str:
    """Extract text from PDF using LLM vision (page by page)."""
    dpi = config.get("ocr", {}).get("dpi", 200)
    
    print(f"    Converting PDF to images...")
    images_b64 = pdf_to_base64_images(pdf_path, dpi=dpi)
    
    all_text = []
    system_prompt = get_extraction_prompt(is_handwritten)
    
    for i, img_b64 in enumerate(images_b64):
        print(f"    OCR page {i + 1}/{len(images_b64)}...")
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }
        ]
        
        extracted = await call_groq_api(messages, config, max_tokens=2000)
        all_text.append(f"--- Page {i + 1} ---\n{extracted}")
    
    return "\n\n".join(all_text)


async def holistic_evaluate(
    question_text: str,
    answer_key_text: str,
    student_text: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    HOLISTIC EVALUATION - Single LLM call with full context.
    
    Uses Qwen3-VL via Fireworks AI for superior reasoning:
    - Feed ALL three documents to the LLM
    - Let it understand, align, and evaluate like a human examiner
    - Get structured JSON result in one call
    """
    print("  [HOLISTIC] Building comprehensive evaluation prompt...")
    print("  [HOLISTIC] Using Qwen3-VL via Fireworks AI for evaluation...")
    
    # Get the holistic prompt from config
    holistic_prompt = config.get("holistic_evaluation_prompt", "")
    
    # Qwen3-VL has much larger context - increase limits significantly
    # 32k tokens ≈ 96k chars, but we leave room for output
    question_truncated = truncate_for_holistic(question_text, 15000)
    answer_truncated = truncate_for_holistic(answer_key_text, 12000)
    student_truncated = truncate_for_holistic(student_text, 15000)
    
    # Build the complete prompt with all documents
    full_prompt = f"""{holistic_prompt}

================================================
QUESTION PAPER
================================================
{question_truncated}

================================================
ANSWER KEY
================================================
{answer_truncated}

================================================
STUDENT ANSWER SCRIPT
================================================
{student_truncated}

================================================
NOW EVALUATE AND RETURN JSON
================================================
"""

    messages = [
        {
            "role": "system", 
            "content": "You are an expert university examiner. Evaluate holistically like a human. Think step by step, then return ONLY valid JSON as your final output."
        },
        {"role": "user", "content": full_prompt}
    ]
    
    print("  [HOLISTIC] Calling Qwen3-VL (Fireworks AI) for complete evaluation...")
    response = await call_fireworks_api(messages, config, max_tokens=8000)
    
    print("  [HOLISTIC] Parsing evaluation result...")
    result = extract_json_from_response(response)
    
    return result


def validate_and_fix_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and fix the holistic evaluation result.
    Ensures all required fields exist and values are valid.
    """
    # Default structure
    default_result = {
        "section_wise_evaluation": {
            "A": {"questions": {}, "retained": [], "section_total": 0},
            "B": {"questions": {}, "retained": [], "section_total": 0},
            "C": {"questions": {}, "retained": [], "section_total": 0}
        },
        "final_summary": {
            "total_marks": 0,
            "max_marks": 50,
            "result": "FAIL",
            "examiner_comment": "Evaluation incomplete"
        }
    }
    
    if "section_wise_evaluation" not in result:
        result["section_wise_evaluation"] = default_result["section_wise_evaluation"]
    
    if "final_summary" not in result:
        result["final_summary"] = default_result["final_summary"]
    
    # Validate section totals
    for section in ["A", "B", "C"]:
        if section not in result["section_wise_evaluation"]:
            result["section_wise_evaluation"][section] = default_result["section_wise_evaluation"][section]
        
        section_data = result["section_wise_evaluation"][section]
        
        # Ensure section_total is capped correctly
        max_section = 10 if section == "A" else 20
        if section_data.get("section_total", 0) > max_section:
            section_data["section_total"] = max_section
    
    # Validate total marks
    section_a = result["section_wise_evaluation"]["A"].get("section_total", 0)
    section_b = result["section_wise_evaluation"]["B"].get("section_total", 0)
    section_c = result["section_wise_evaluation"]["C"].get("section_total", 0)
    
    computed_total = section_a + section_b + section_c
    result["final_summary"]["total_marks"] = min(computed_total, 50)
    result["final_summary"]["max_marks"] = 50
    
    # Validate result
    if result["final_summary"]["total_marks"] >= 25:
        result["final_summary"]["result"] = "PASS"
    else:
        result["final_summary"]["result"] = "FAIL"
    
    return result


def generate_report(result: Dict[str, Any]) -> str:
    """Generate a human-readable report from the evaluation result."""
    lines = []
    lines.append("=" * 60)
    lines.append("HOLISTIC EXAM EVALUATION REPORT")
    lines.append("=" * 60)
    
    sections = result.get("section_wise_evaluation", {})
    
    for section_name in ["A", "B", "C"]:
        section = sections.get(section_name, {})
        questions = section.get("questions", {})
        retained = section.get("retained", [])
        total = section.get("section_total", 0)
        
        lines.append(f"\n--- SECTION {section_name} ---")
        
        for q_id, q_data in questions.items():
            awarded = q_data.get("awarded", 0)
            max_marks = q_data.get("max", 5 if section_name == "A" else 10)
            remarks = q_data.get("remarks", "")
            retained_mark = "✓" if q_id in retained else "✗"
            lines.append(f"  {q_id}: {awarded}/{max_marks} {retained_mark} - {remarks[:50]}")
        
        lines.append(f"  Section Total: {total}/{10 if section_name == 'A' else 20}")
    
    summary = result.get("final_summary", {})
    lines.append("\n" + "=" * 60)
    lines.append(f"TOTAL: {summary.get('total_marks', 0)}/{summary.get('max_marks', 50)}")
    lines.append(f"RESULT: {summary.get('result', 'UNKNOWN')}")
    lines.append(f"Comment: {summary.get('examiner_comment', '')}")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def save_result(job_id: str, result: Dict[str, Any], outputs_dir: str) -> str:
    """Save evaluation result to JSON file."""
    outputs_path = Path(outputs_dir)
    outputs_path.mkdir(parents=True, exist_ok=True)
    
    output_file = outputs_path / f"{job_id}_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    return str(output_file)


async def evaluate_exam(
    job_id: str,
    question_pdf_path: str,
    answer_key_pdf_path: str,
    student_pdf_path: str
) -> Dict[str, Any]:
    """
    Main evaluation pipeline - PT-II ONLY.
    
    NEW 3-STAGE HOLISTIC PIPELINE:
    1. OCR extraction (page by page) - QP/AK cached at exam level
    2. Holistic evaluation (SINGLE LLM call)
    3. Validation and save (no LLM)
    
    IMPORTANT: Question Paper and Answer Key OCR is cached at EXAM level.
    Only student answer OCR runs for each new student.
    """
    config = load_config()
    checkpoint = CheckpointService(job_id, config.get("paths", {}).get("checkpoints", "./checkpoints"))
    outputs_dir = config.get("paths", {}).get("outputs", "./outputs")
    checkpoints_dir = config.get("paths", {}).get("checkpoints", "./checkpoints")
    
    # Generate exam_id from QP + AK file hashes (same QP+AK = same exam_id)
    exam_id = generate_exam_id(question_pdf_path, answer_key_pdf_path)
    exam_checkpoint = ExamCheckpointService(exam_id, checkpoints_dir)
    
    print(f"[{job_id}] Exam ID: {exam_id}")
    
    try:
        # ============ STAGE 1: OCR EXTRACTION ============
        # First check per-job checkpoint (for resume capability)
        job_ocr_texts = checkpoint.get_ocr_texts()
        
        if job_ocr_texts and job_ocr_texts.get("student_answers"):
            # Full job checkpoint exists - resume from it
            print(f"[{job_id}] ✓ OCR already complete, loading from job checkpoint")
            question_text = job_ocr_texts["question_paper"]
            answer_key_text = job_ocr_texts["answer_key"]
            student_text = job_ocr_texts["student_answers"]
        else:
            print(f"[{job_id}] STAGE 1: OCR Extraction")
            job_store.update_job(job_id, "processing", error=None)
            
            # Check exam-level checkpoint for QP and AK
            exam_ocr = exam_checkpoint.get_ocr_texts()
            
            if exam_ocr:
                # EXAM CHECKPOINT EXISTS - Skip QP and AK OCR
                print(f"[{job_id}] ✓ Using cached exam OCR for exam_id: {exam_id}")
                print(f"[{job_id}]   Skipping question paper OCR (cached)")
                print(f"[{job_id}]   Skipping answer key OCR (cached)")
                question_text = exam_ocr["question_paper"]
                answer_key_text = exam_ocr["answer_key"]
            else:
                # FIRST STUDENT - Extract QP and AK, then cache
                print(f"[{job_id}]   Processing question paper (FIRST TIME)...")
                question_text = await extract_text_with_llm(question_pdf_path, config, is_handwritten=False)
                
                print(f"[{job_id}]   Processing answer key (FIRST TIME)...")
                answer_key_text = await extract_text_with_llm(answer_key_pdf_path, config, is_handwritten=False)
                
                # Save to exam checkpoint for reuse by future students
                exam_checkpoint.save_ocr_results(question_text, answer_key_text)
                print(f"[{job_id}] ✓ Exam OCR checkpoint saved (exam_id: {exam_id})")
            
            # ALWAYS OCR student answers (unique per student)
            print(f"[{job_id}]   Processing student answers (handwriting recognition)...")
            student_text = await extract_text_with_llm(student_pdf_path, config, is_handwritten=True)
            
            # Save per-job OCR checkpoint (for resume capability)
            checkpoint.save_ocr_complete(question_text, answer_key_text, student_text)
            print(f"[{job_id}] ✓ Job OCR checkpoint saved")
        
        # ============ STAGE 2: HOLISTIC EVALUATION ============
        print(f"[{job_id}] STAGE 2: Holistic Evaluation (Single LLM Call)")
        
        evaluation_result = await holistic_evaluate(
            question_text, 
            answer_key_text, 
            student_text, 
            config
        )
        
        print(f"[{job_id}] ✓ Holistic evaluation complete")
        
        # ============ STAGE 3: VALIDATION & SAVE ============
        print(f"[{job_id}] STAGE 3: Validation & Final Processing")
        
        # Validate and fix any issues
        final_result = validate_and_fix_result(evaluation_result)
        
        # Save checkpoint
        checkpoint.save_final_result(final_result)
        
        # Save to outputs directory
        result_path = save_result(job_id, final_result, outputs_dir)
        print(f"[{job_id}] ✓ Result saved to {result_path}")
        
        # Generate and print report
        report = generate_report(final_result)
        print(f"\n{report}\n")
        
        # Update job status
        job_store.update_job(job_id, "completed", result=final_result)
        
        total = final_result.get("final_summary", {}).get("total_marks", 0)
        result_str = final_result.get("final_summary", {}).get("result", "UNKNOWN")
        print(f"[{job_id}] ✅ Evaluation complete! {result_str} ({total}/50)")
        
        return final_result
    
    except Exception as e:
        error_msg = str(e)
        print(f"[{job_id}] ❌ Error: {error_msg}")
        print(f"[{job_id}] 💾 Progress saved in checkpoint - can resume later")
        job_store.update_job(job_id, "failed", error=error_msg)
        raise


async def resume_evaluation(job_id: str) -> Dict[str, Any]:
    """
    Resume a failed or interrupted evaluation from its checkpoint.
    """
    config = load_config()
    checkpoint = CheckpointService(job_id, config.get("paths", {}).get("checkpoints", "./checkpoints"))
    
    existing = checkpoint.load()
    if not existing:
        raise ValueError(f"No checkpoint found for job {job_id}")
    
    print(f"[{job_id}] Resuming from stage: {existing.get('stage', 'UNKNOWN')}")
    
    # Get file paths from uploads
    uploads_dir = Path(config.get("paths", {}).get("uploads", "./uploads"))
    job_dir = uploads_dir / job_id
    
    question_path = job_dir / "question_paper.pdf"
    answer_path = job_dir / "answer_key.pdf"
    student_path = job_dir / "student_sheet.pdf"
    
    if not all(p.exists() for p in [question_path, answer_path, student_path]):
        raise ValueError(f"Missing PDF files for job {job_id}")
    
    return await evaluate_exam(
        job_id,
        str(question_path),
        str(answer_path),
        str(student_path)
    )


async def run_evaluation_task(
    job_id: str,
    question_pdf_path: str,
    answer_key_pdf_path: str,
    student_pdf_path: str
):
    """Background task wrapper."""
    try:
        await evaluate_exam(job_id, question_pdf_path, answer_key_pdf_path, student_pdf_path)
    except Exception as e:
        print(f"[{job_id}] Background task failed: {e}")
