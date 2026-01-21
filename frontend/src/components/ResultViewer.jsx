import React from 'react';

function getMarksClass(awarded, max) {
    if (awarded === max) return 'full';
    if (awarded === 0) return 'zero';
    return 'partial';
}

export default function ResultViewer({ result }) {
    if (!result) return null;

    const { student_id, sections, grand_total, overall_feedback } = result;

    return (
        <div className="results-container">
            <div className="grand-total">
                <div className="label">Grand Total</div>
                <div className="score">{grand_total}</div>
            </div>

            {Object.entries(sections || {}).map(([sectionName, section]) => (
                <div key={sectionName} className="section-result">
                    <div className="section-header">
                        <div className="section-name">Section {sectionName}</div>
                        <div className="section-score">{section.section_total} marks</div>
                    </div>

                    {Object.entries(section.questions || {}).map(([qId, q]) => {
                        const isDiscarded = section.discarded_questions?.includes(qId);

                        return (
                            <div key={qId} className="question-result">
                                <div className="question-header">
                                    <div className={`question-id ${isDiscarded ? 'discarded' : ''}`}>
                                        {qId}
                                        {isDiscarded && <span className="badge badge-discarded">Discarded</span>}
                                    </div>
                                    <div className={`question-marks ${getMarksClass(q.marks_awarded, q.max_marks)}`}>
                                        {q.marks_awarded} / {q.max_marks}
                                    </div>
                                </div>
                                <div className="question-feedback">{q.feedback}</div>
                            </div>
                        );
                    })}
                </div>
            ))}

            {overall_feedback && (
                <div className="overall-feedback">
                    <h4>Overall Feedback</h4>
                    <p>{overall_feedback}</p>
                </div>
            )}
        </div>
    );
}
