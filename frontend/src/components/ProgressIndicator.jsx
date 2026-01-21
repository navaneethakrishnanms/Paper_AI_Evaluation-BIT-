/**
 * ProgressIndicator - Shows overall evaluation progress.
 * Displays current student count, progress bar, and status.
 */
import React from 'react';
import { useEvaluation } from '../context/EvaluationContext';

export default function ProgressIndicator() {
    const { state, computed } = useEvaluation();

    if (!state.isProcessing && state.jobs.length === 0) {
        return null;
    }

    const { completedCount, failedCount, totalCount } = computed;
    const processedCount = completedCount + failedCount;
    const progressPercent = totalCount > 0 ? (processedCount / totalCount) * 100 : 0;

    // Determine current status message
    let statusMessage = '';
    let statusClass = '';

    if (state.isProcessing) {
        const currentJob = state.jobs[state.currentJobIndex];
        if (currentJob) {
            statusMessage = `Processing: ${currentJob.filename}`;
            if (currentJob.stage) {
                statusMessage += ` — ${currentJob.stage}`;
            }
        } else {
            statusMessage = 'Starting evaluation...';
        }
        statusClass = 'processing';
    } else if (processedCount === totalCount && totalCount > 0) {
        if (failedCount === 0) {
            statusMessage = 'All evaluations completed successfully!';
            statusClass = 'success';
        } else if (completedCount === 0) {
            statusMessage = 'All evaluations failed';
            statusClass = 'error';
        } else {
            statusMessage = `Completed with ${failedCount} error${failedCount > 1 ? 's' : ''}`;
            statusClass = 'warning';
        }
    }

    return (
        <div className={`progress-indicator ${statusClass}`}>
            <div className="progress-header">
                <div className="progress-title">
                    <span className="progress-icon">
                        {state.isProcessing ? '⚙️' : (failedCount > 0 ? '⚠️' : '✅')}
                    </span>
                    Evaluation Progress
                </div>
                <div className="progress-count">
                    {processedCount} / {totalCount} students
                </div>
            </div>

            <div className="progress-bar-container">
                <div
                    className="progress-bar-fill"
                    style={{ width: `${progressPercent}%` }}
                />
            </div>

            <div className="progress-status">
                {statusMessage}
            </div>

            {/* Stats */}
            <div className="progress-stats">
                <div className="stat completed">
                    <span className="stat-value">{completedCount}</span>
                    <span className="stat-label">Completed</span>
                </div>
                <div className="stat failed">
                    <span className="stat-value">{failedCount}</span>
                    <span className="stat-label">Failed</span>
                </div>
                <div className="stat pending">
                    <span className="stat-value">{totalCount - processedCount}</span>
                    <span className="stat-label">Pending</span>
                </div>
            </div>
        </div>
    );
}
