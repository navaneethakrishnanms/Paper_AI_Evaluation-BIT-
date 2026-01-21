import React, { useEffect } from 'react';

export default function ProgressTracker({ status, onPollStatus }) {
    useEffect(() => {
        if (status === 'processing') {
            const interval = setInterval(onPollStatus, 2000);
            return () => clearInterval(interval);
        }
    }, [status, onPollStatus]);

    if (status !== 'processing') return null;

    return (
        <div className="card">
            <div className="progress-container">
                <div className="progress-spinner"></div>
                <div className="progress-status">Evaluating Exam...</div>
                <div className="progress-message">
                    This may take 1-2 minutes depending on document length.
                    <br />
                    Processing: OCR → Structure Analysis → Evaluation → Scoring
                </div>
            </div>
        </div>
    );
}
