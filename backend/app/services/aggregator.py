"""
Aggregator Service - Stage 6
Final aggregation of evaluation results (NO LLM CALL).

PT-II ONLY:
- Section A: Best 2 of 3 questions, max 10 marks
- Section B: Best 2 of 3 questions, max 20 marks
- Section C: Best 2 of 3 questions, max 20 marks
- Total: 50 marks, Pass: 25+

Applies:
- Answer-any-2 rule (keep best 2 per section)
- Section caps
- Computes grand total, percentage, grade
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


# Fixed section configuration for PT-II
SECTION_CONFIG = {
    "A": {"max_marks": 10, "retain_best": 2, "question_max": 5},
    "B": {"max_marks": 20, "retain_best": 2, "question_max": 10},
    "C": {"max_marks": 20, "retain_best": 2, "question_max": 10}
}

TOTAL_MAX = 50
PASS_MARKS = 25


def get_section_max_marks(section: str) -> int:
    """Get maximum evaluated marks for a section."""
    return SECTION_CONFIG.get(section, {}).get("max_marks", 10)


def calculate_question_total(question_data: Dict[str, Any]) -> float:
    """Calculate total marks for a question from subdivisions or direct field."""
    # Check for question_total first
    if "question_total" in question_data:
        return float(question_data["question_total"])
    
    # Check for total_awarded
    if "total_awarded" in question_data:
        return float(question_data["total_awarded"])
    
    # Check for marks_awarded (backward compat)
    if "marks_awarded" in question_data:
        return float(question_data["marks_awarded"])
    
    # Sum from subdivisions
    subdivisions = question_data.get("subdivisions", {})
    total = 0.0
    for sub_id, sub_data in subdivisions.items():
        if isinstance(sub_data, dict):
            total += float(sub_data.get("marks_awarded", 0))
    
    return total


def get_question_max(question_data: Dict[str, Any], section: str) -> float:
    """Get maximum marks for a question."""
    # Check for question_max first
    if "question_max" in question_data:
        return float(question_data["question_max"])
    
    # Check for max_marks
    if "max_marks" in question_data:
        return float(question_data["max_marks"])
    
    # Use section default
    return float(SECTION_CONFIG.get(section, {}).get("question_max", 5))


def apply_answer_any_two_rule(
    section_result: Dict[str, Any],
    section: str
) -> Tuple[List[str], List[str], float]:
    """
    Apply the answer-any-two rule for a section.
    
    Returns:
        (retained_questions, discarded_questions, section_total)
    """
    questions = section_result.get("questions", {})
    max_allowed = get_section_max_marks(section)
    retain_count = SECTION_CONFIG.get(section, {}).get("retain_best", 2)
    
    # Collect (question_id, marks_awarded) tuples
    question_scores = []
    for q_id, q_data in questions.items():
        if isinstance(q_data, dict):
            marks_awarded = calculate_question_total(q_data)
            question_scores.append((q_id, marks_awarded))
    
    # Sort by marks awarded (highest first)
    question_scores.sort(key=lambda x: x[1], reverse=True)
    
    if len(question_scores) <= retain_count:
        # Student answered fewer than required - keep all
        retained = [qs[0] for qs in question_scores]
        discarded = []
        section_total = sum(qs[1] for qs in question_scores)
    else:
        # Student answered more - keep best N
        retained = [qs[0] for qs in question_scores[:retain_count]]
        discarded = [qs[0] for qs in question_scores[retain_count:]]
        section_total = sum(qs[1] for qs in question_scores[:retain_count])
    
    # Cap at max allowed for the section
    section_total = min(section_total, max_allowed)
    
    return retained, discarded, section_total


def compute_final_result(
    section_results: Dict[str, Dict[str, Any]],
    student_id: str = "UNKNOWN"
) -> Dict[str, Any]:
    """
    Compute the final aggregated result from all section evaluations.
    This is pure computation - NO LLM calls.
    
    Args:
        section_results: Dict with keys A, B, C containing section evaluation results
        student_id: Student identifier
    
    Returns:
        Final evaluation result with grand total
    """
    final_result = {
        "student_id": student_id,
        "exam_mode": "PT-II",
        "sections": {},
        "section_totals": {},
        "grand_total": 0,
        "max_possible": TOTAL_MAX,
        "percentage": 0.0,
        "grade": "",
        "result": "",
        "overall_feedback": "",
        "evaluation_summary": [],
        "audit_log": []
    }
    
    section_feedback = []
    
    for section in ["A", "B", "C"]:
        if section not in section_results:
            # Section not evaluated - add empty result
            final_result["sections"][section] = {
                "retained_questions": [],
                "discarded_questions": [],
                "questions": {},
                "section_total": 0,
                "section_max": get_section_max_marks(section)
            }
            final_result["section_totals"][section] = 0
            section_feedback.append(f"Section {section}: 0/{get_section_max_marks(section)} (not evaluated)")
            continue
        
        sr = section_results[section]
        section_max = get_section_max_marks(section)
        
        # Apply answer-any-two rule
        retained, discarded, section_total = apply_answer_any_two_rule(sr, section)
        
        # Get question details
        questions = sr.get("questions", {})
        
        final_result["sections"][section] = {
            "retained_questions": retained,
            "discarded_questions": discarded,
            "questions": questions,
            "section_total": section_total,
            "section_max": section_max
        }
        
        final_result["section_totals"][section] = section_total
        final_result["grand_total"] += section_total
        
        # Build section feedback
        if discarded:
            discarded_q = discarded[0]
            discarded_marks = calculate_question_total(questions.get(discarded_q, {}))
            section_feedback.append(
                f"Section {section}: {section_total}/{section_max} "
                f"(dropped {discarded_q} with {discarded_marks:.0f} marks)"
            )
            final_result["audit_log"].append(
                f"Dropped {discarded_q} (lowest in Section {section})"
            )
        else:
            section_feedback.append(f"Section {section}: {section_total}/{section_max}")
    
    # Calculate percentage and grade
    if TOTAL_MAX > 0:
        final_result["percentage"] = round((final_result["grand_total"] / TOTAL_MAX) * 100, 1)
    
    final_result["grade"] = calculate_grade(final_result["percentage"])
    final_result["result"] = "PASS" if final_result["grand_total"] >= PASS_MARKS else "FAIL"
    
    # Generate overall feedback
    final_result["overall_feedback"] = generate_overall_feedback(
        final_result["grand_total"],
        final_result["percentage"],
        section_feedback,
        final_result["result"]
    )
    
    final_result["evaluation_summary"] = section_feedback
    
    return final_result


def calculate_grade(percentage: float) -> str:
    """Calculate letter grade from percentage."""
    if percentage >= 90:
        return "O"  # Outstanding
    elif percentage >= 80:
        return "A+"
    elif percentage >= 70:
        return "A"
    elif percentage >= 60:
        return "B+"
    elif percentage >= 55:
        return "B"
    elif percentage >= 50:
        return "C"
    elif percentage >= 45:
        return "D"
    else:
        return "F"


def generate_overall_feedback(
    grand_total: float,
    percentage: float,
    section_feedback: List[str],
    result: str
) -> str:
    """Generate human-readable overall feedback."""
    feedback_parts = []
    
    # Result header
    feedback_parts.append(f"Exam: Periodical Test - II")
    feedback_parts.append(f"Result: {result}")
    
    # Performance assessment
    if percentage >= 80:
        feedback_parts.append("Excellent performance! Strong understanding of concepts.")
    elif percentage >= 60:
        feedback_parts.append("Good performance with solid grasp of fundamentals.")
    elif percentage >= 50:
        feedback_parts.append("Average performance. Some concepts need more attention.")
    elif percentage >= 40:
        feedback_parts.append("Below average. Focus on understanding core concepts.")
    else:
        feedback_parts.append("Needs significant improvement. Review all topics thoroughly.")
    
    # Add section breakdown
    feedback_parts.append("\nSection breakdown:")
    feedback_parts.extend([f"  • {sf}" for sf in section_feedback])
    
    # Final summary
    feedback_parts.append(f"\nFinal Score: {grand_total:.0f}/50 ({percentage}%)")
    
    return "\n".join(feedback_parts)


def save_final_result(job_id: str, result: Dict[str, Any], outputs_dir: str) -> str:
    """Save final result to JSON file."""
    outputs_path = Path(outputs_dir)
    outputs_path.mkdir(parents=True, exist_ok=True)
    
    output_file = outputs_path / f"{job_id}_final_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    return str(output_file)


def generate_detailed_report(result: Dict[str, Any]) -> str:
    """
    Generate a detailed text report from the evaluation result.
    Useful for printing or display.
    """
    lines = [
        "=" * 60,
        "EXAM EVALUATION REPORT",
        "=" * 60,
        f"Student ID: {result.get('student_id', 'UNKNOWN')}",
        f"Exam: Periodical Test - II",
        f"Result: {result.get('result', 'N/A')}",
        f"Grade: {result.get('grade', 'N/A')}",
        f"Total: {result.get('grand_total', 0):.0f}/50 ({result.get('percentage', 0)}%)",
        "-" * 60,
        ""
    ]
    
    for section in ["A", "B", "C"]:
        if section not in result.get("sections", {}):
            continue
        
        section_data = result["sections"][section]
        lines.append(f"SECTION {section}:")
        lines.append(f"  Total: {section_data.get('section_total', 0):.0f}/{section_data.get('section_max', 0)}")
        lines.append(f"  Retained: {', '.join(section_data.get('retained_questions', []))}")
        
        if section_data.get('discarded_questions'):
            lines.append(f"  Discarded: {', '.join(section_data['discarded_questions'])} (lowest score)")
        
        lines.append("")
        
        # Question details
        for q_id, q_data in section_data.get("questions", {}).items():
            if isinstance(q_data, dict):
                status = "✓" if q_id in section_data.get('retained_questions', []) else "✗"
                total_awarded = calculate_question_total(q_data)
                max_marks = get_question_max(q_data, section)
                feedback = q_data.get('feedback', 'No feedback')
                if len(feedback) > 50:
                    feedback = feedback[:47] + "..."
                lines.append(
                    f"    {status} {q_id}: {total_awarded:.0f}/{max_marks:.0f} - {feedback}"
                )
        
        lines.append("")
    
    lines.append("-" * 60)
    lines.append(result.get("overall_feedback", ""))
    lines.append("=" * 60)
    
    return "\n".join(lines)


def create_output_json(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create the final output JSON in the specified format.
    """
    return {
        "student_id": result.get("student_id", "UNKNOWN"),
        "exam": "PT-II",
        "section_scores": {
            section: {
                "retained": result["sections"].get(section, {}).get("retained_questions", []),
                "score": result["section_totals"].get(section, 0)
            }
            for section in ["A", "B", "C"]
        },
        "grand_total": result.get("grand_total", 0),
        "percentage": result.get("percentage", 0),
        "result": result.get("result", "FAIL"),
        "audit_log": result.get("audit_log", [])
    }
