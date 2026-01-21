/**
 * ResultModal - Modal showing detailed evaluation results for a student.
 * Displays marks breakdown, section details, and overall feedback.
 */
import React from 'react';
import { useEvaluation } from '../context/EvaluationContext';

function SectionResult({ section, sectionKey, data }) {
    if (!data) return null;

    // Determine max marks based on section
    const sectionMaxMarks = sectionKey === 'A' ? 10 : 20;

    // Check if question is in retained list
    const retained = data.retained || [];

    return (
        <div className="section-result">
            <div className="section-header">
                <h4 className="section-name">{section}</h4>
                <div className="section-score">
                    {data.section_total || 0} / {sectionMaxMarks}
                </div>
            </div>

            {data.questions && (
                <div className="questions-list">
                    {Object.entries(data.questions).map(([qId, qData]) => {
                        const isRetained = retained.includes(qId);
                        const awarded = qData.awarded ?? qData.marks ?? 0;
                        const maxMarks = qData.max ?? qData.max_marks ?? (sectionKey === 'A' ? 5 : 10);

                        return (
                            <div key={qId} className={`question-item ${!isRetained ? 'discarded' : ''}`}>
                                <div className="question-header">
                                    <span className="question-id">
                                        {qId}
                                        {!isRetained && <span className="badge-discarded">discarded</span>}
                                    </span>
                                    <span className={`question-marks ${awarded === maxMarks ? 'full' :
                                            awarded === 0 ? 'zero' : 'partial'
                                        }`}>
                                        {awarded} / {maxMarks}
                                    </span>
                                </div>
                                {qData.remarks && (
                                    <div className="question-feedback">{qData.remarks}</div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

export default function ResultModal() {
    const { state, actions } = useEvaluation();

    // Find the selected job
    const selectedJob = state.jobs.find(j => j.id === state.selectedJobId);

    if (!selectedJob || !selectedJob.result) {
        return null;
    }

    const result = selectedJob.result;

    // Extract from final_summary (backend structure)
    const summary = result.final_summary || {};
    const totalMarks = summary.total_marks ?? result.grand_total ?? result.total_marks ?? 0;
    const maxMarks = summary.max_marks ?? result.max_marks ?? 50;
    const percentage = ((totalMarks / maxMarks) * 100).toFixed(1);
    const resultStatus = summary.result || result.result;
    const passed = resultStatus === 'PASS';
    const examinerComment = summary.examiner_comment || result.overall_feedback || '';

    // Extract sections from section_wise_evaluation (backend structure)
    const sections = result.section_wise_evaluation || {};

    const handleClose = () => {
        actions.selectJob(null);
    };

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">
                        Evaluation Results
                    </h2>
                    <button className="modal-close" onClick={handleClose}>
                        ✕
                    </button>
                </div>

                <div className="modal-body">
                    {/* Student Info */}
                    <div className="result-student-info">
                        <div className="student-filename">{selectedJob.filename}</div>
                        <div className="student-jobid">Job ID: {selectedJob.jobId}</div>
                    </div>

                    {/* Grand Total */}
                    <div className={`grand-total-card ${passed ? 'passed' : 'failed'}`}>
                        <div className="grand-total-label">Total Score</div>
                        <div className="grand-total-score">
                            {totalMarks} / {maxMarks}
                        </div>
                        <div className="grand-total-percentage">
                            {percentage}%
                        </div>
                        <div className={`grand-total-status ${passed ? 'pass' : 'fail'}`}>
                            {passed ? 'PASSED' : 'FAILED'}
                        </div>
                    </div>

                    {/* Section Results */}
                    <div className="sections-container">
                        {sections.A && (
                            <SectionResult section="Section A" sectionKey="A" data={sections.A} />
                        )}
                        {sections.B && (
                            <SectionResult section="Section B" sectionKey="B" data={sections.B} />
                        )}
                        {sections.C && (
                            <SectionResult section="Section C" sectionKey="C" data={sections.C} />
                        )}
                    </div>

                    {/* Overall Feedback */}
                    {examinerComment && (
                        <div className="overall-feedback">
                            <h4>Examiner's Comment</h4>
                            <p>{examinerComment}</p>
                        </div>
                    )}
                </div>

                <div className="modal-footer">
                    <button className="btn-secondary" onClick={handleClose}>
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
