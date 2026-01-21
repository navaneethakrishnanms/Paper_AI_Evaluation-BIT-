/**
 * AI Exam Evaluation System - Main Application
 * Professional exam-portal style frontend with batch evaluation support.
 */
import React, { useRef, useCallback } from 'react';
import { EvaluationProvider, useEvaluation } from './context/EvaluationContext';
import ModeSelector from './components/ModeSelector';
import MasterFileUpload from './components/MasterFileUpload';
import StudentFileUpload from './components/StudentFileUpload';
import StudentQueueTable from './components/StudentQueueTable';
import ProgressIndicator from './components/ProgressIndicator';
import ResultModal from './components/ResultModal';
import { processQueue } from './services/jobQueue';

/**
 * Main App Content - Uses the evaluation context
 */
function AppContent() {
    const { state, actions, computed } = useEvaluation();
    const abortControllerRef = useRef(null);

    /**
     * Start the evaluation process
     */
    const handleStartEvaluation = useCallback(async () => {
        // Initialize the job queue
        actions.startProcessing();

        // Create abort controller for cancellation
        abortControllerRef.current = new AbortController();

        // Process all students
        await processQueue(
            state.masterFiles.questionPaper,
            state.masterFiles.answerKey,
            state.studentFiles,
            {
                onJobStart: (index, filename) => {
                    actions.setCurrentJob(index);
                    actions.updateJob(index, {
                        status: 'uploading',
                        stage: 'Starting...'
                    });
                },
                onJobUpdate: (index, update) => {
                    actions.updateJob(index, update);
                },
                onJobComplete: (index, result) => {
                    if (result.success) {
                        actions.updateJob(index, {
                            status: 'completed',
                            stage: 'Completed',
                            result: result.result,
                            jobId: result.jobId,
                        });
                    } else {
                        actions.updateJob(index, {
                            status: 'failed',
                            stage: 'Failed',
                            error: result.error,
                            jobId: result.jobId,
                        });
                    }
                },
                onAllComplete: () => {
                    actions.stopProcessing();
                },
            },
            abortControllerRef.current.signal
        );
    }, [state.masterFiles, state.studentFiles, actions]);

    /**
     * Clear all files and reset
     */
    const handleClearAll = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        actions.clearAll();
    }, [actions]);

    /**
     * Start a new evaluation session (keep master files, reset students)
     */
    const handleNewSession = useCallback(() => {
        actions.resetJobs();
    }, [actions]);

    /**
     * Download results as CSV file
     */
    const handleDownloadCSV = useCallback(() => {
        // Filter only completed jobs
        const completedJobs = state.jobs.filter(j => j.status === 'completed' && j.result);

        if (completedJobs.length === 0) {
            alert('No completed evaluations to download.');
            return;
        }

        // CSV header
        const headers = ['Job ID', 'Filename', 'Total Marks', 'Max Marks', 'Result'];

        // CSV rows
        const rows = completedJobs.map(job => {
            const summary = job.result.final_summary || {};
            const totalMarks = summary.total_marks ?? 0;
            const maxMarks = summary.max_marks ?? 50;
            const result = summary.result ?? 'N/A';

            return [
                job.jobId || '',
                job.filename || '',
                totalMarks,
                maxMarks,
                result
            ];
        });

        // Build CSV content
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        // Create download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `evaluation_results_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }, [state.jobs]);

    // Check if we're in results phase
    const showingResults = state.jobs.length > 0 && !state.isProcessing;
    const showingQueue = state.isProcessing || state.jobs.length > 0;
    const hasCompletedJobs = state.jobs.some(j => j.status === 'completed');

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <h1>AI Exam Evaluator</h1>
                <p>Automated answer sheet evaluation system</p>
            </header>

            {/* Main Content */}
            <main className="main-content">
                {/* Mode Selection */}
                <div className="card mode-card">
                    <ModeSelector disabled={state.isProcessing} />
                </div>

                {/* Upload Section */}
                {!showingQueue && (
                    <div className="card upload-card">
                        <MasterFileUpload disabled={state.isProcessing} />
                        <div className="divider" />
                        <StudentFileUpload disabled={state.isProcessing} />
                    </div>
                )}

                {/* Progress Indicator */}
                {showingQueue && <ProgressIndicator />}

                {/* Queue Table */}
                {showingQueue && <StudentQueueTable />}

                {/* Action Buttons */}
                <div className="actions-section">
                    {!showingQueue && (
                        <button
                            className="btn btn-primary btn-large"
                            onClick={handleStartEvaluation}
                            disabled={!computed.canStartEvaluation}
                        >
                            <span className="btn-icon">🚀</span>
                            Start Evaluation
                        </button>
                    )}

                    {showingResults && (
                        <button
                            className="btn btn-secondary"
                            onClick={handleNewSession}
                        >
                            <span className="btn-icon">📝</span>
                            New Batch
                        </button>
                    )}

                    {hasCompletedJobs && (
                        <button
                            className="btn btn-primary"
                            onClick={handleDownloadCSV}
                        >
                            <span className="btn-icon">📥</span>
                            Download CSV
                        </button>
                    )}

                    <button
                        className="btn btn-secondary btn-clear"
                        onClick={handleClearAll}
                        disabled={state.isProcessing}
                    >
                        <span className="btn-icon">🗑️</span>
                        Clear All
                    </button>
                </div>

                {/* Validation Messages */}
                {!computed.canStartEvaluation && !showingQueue && (
                    <div className="validation-hints">
                        {!state.masterFiles.questionPaper && (
                            <div className="hint">📄 Upload a Question Paper</div>
                        )}
                        {!state.masterFiles.answerKey && (
                            <div className="hint">✓ Upload an Answer Key</div>
                        )}
                        {state.studentFiles.length === 0 && (
                            <div className="hint">✍️ Upload at least one Student Answer Sheet</div>
                        )}
                    </div>
                )}
            </main>

            {/* Result Modal */}
            <ResultModal />

            {/* Footer */}
            <footer className="footer">
                <p>AI Exam Evaluation System v2.0 — PT-II Mode</p>
            </footer>
        </div>
    );
}

/**
 * Root App Component with Provider
 */
export default function App() {
    return (
        <EvaluationProvider>
            <AppContent />
        </EvaluationProvider>
    );
}
