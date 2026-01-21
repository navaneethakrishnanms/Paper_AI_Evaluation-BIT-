/**
 * StudentQueueTable - Displays all students with their evaluation status.
 * Shows job ID, status, marks, and allows viewing results.
 */
import React from 'react';
import { useEvaluation } from '../context/EvaluationContext';

// Status badge configuration
const STATUS_CONFIG = {
    waiting: { label: 'Waiting', className: 'status-waiting', icon: '⏳' },
    uploading: { label: 'Uploading', className: 'status-uploading', icon: '📤' },
    ocr: { label: 'OCR Running', className: 'status-ocr', icon: '🔍' },
    evaluating: { label: 'Evaluating', className: 'status-evaluating', icon: '📊' },
    completed: { label: 'Completed', className: 'status-completed', icon: '✅' },
    failed: { label: 'Failed', className: 'status-failed', icon: '❌' },
};

function StatusBadge({ status }) {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.waiting;
    return (
        <span className={`status-badge ${config.className}`}>
            <span className="status-icon">{config.icon}</span>
            {config.label}
        </span>
    );
}

function getMarksDisplay(result) {
    if (!result) return '—';

    // Backend returns marks in final_summary object
    const summary = result.final_summary || {};
    const total = summary.total_marks ?? result.grand_total ?? result.total_marks ?? 0;
    const max = summary.max_marks ?? result.max_marks ?? 50;
    return `${total}/${max}`;
}

function getPassFailBadge(result) {
    if (!result) return null;

    // Backend returns result in final_summary object
    const summary = result.final_summary || {};
    const resultStatus = summary.result || result.result;

    if (resultStatus === 'PASS') {
        return <span className="pass-fail-badge pass">PASS</span>;
    } else if (resultStatus === 'FAIL') {
        return <span className="pass-fail-badge fail">FAIL</span>;
    }

    // Fallback: calculate from marks
    const total = summary.total_marks ?? result.grand_total ?? result.total_marks ?? 0;
    const max = summary.max_marks ?? result.max_marks ?? 50;
    const percentage = (total / max) * 100;
    const passed = percentage >= 50;

    return (
        <span className={`pass-fail-badge ${passed ? 'pass' : 'fail'}`}>
            {passed ? 'PASS' : 'FAIL'}
        </span>
    );
}

export default function StudentQueueTable() {
    const { state, actions } = useEvaluation();

    if (state.jobs.length === 0) {
        return null;
    }

    return (
        <div className="queue-section">
            <h3 className="section-title">
                <span className="section-icon">📋</span>
                Evaluation Queue
            </h3>

            <div className="queue-table-wrapper">
                <table className="queue-table">
                    <thead>
                        <tr>
                            <th className="col-num">#</th>
                            <th className="col-filename">Student File</th>
                            <th className="col-jobid">Job ID</th>
                            <th className="col-status">Status</th>
                            <th className="col-marks">Marks</th>
                            <th className="col-result">Result</th>
                            <th className="col-action">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {state.jobs.map((job, index) => (
                            <tr
                                key={job.id}
                                className={`queue-row ${state.currentJobIndex === index ? 'active' : ''}`}
                            >
                                <td className="col-num">{index + 1}</td>
                                <td className="col-filename" title={job.filename}>
                                    {job.filename}
                                </td>
                                <td className="col-jobid">
                                    {job.jobId ? (
                                        <code className="job-id-code">{job.jobId}</code>
                                    ) : (
                                        <span className="no-job-id">—</span>
                                    )}
                                </td>
                                <td className="col-status">
                                    <StatusBadge status={job.status} />
                                </td>
                                <td className="col-marks">
                                    {job.status === 'completed' ? (
                                        <strong>{getMarksDisplay(job.result)}</strong>
                                    ) : (
                                        <span className="marks-pending">—</span>
                                    )}
                                </td>
                                <td className="col-result">
                                    {job.status === 'completed' && getPassFailBadge(job.result)}
                                    {job.status === 'failed' && (
                                        <span className="error-text" title={job.error}>
                                            Error
                                        </span>
                                    )}
                                </td>
                                <td className="col-action">
                                    {job.status === 'completed' && (
                                        <button
                                            className="btn-view"
                                            onClick={() => actions.selectJob(job.id)}
                                        >
                                            View
                                        </button>
                                    )}
                                    {job.status === 'failed' && (
                                        <span className="retry-hint">
                                            Ask to retry
                                        </span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
