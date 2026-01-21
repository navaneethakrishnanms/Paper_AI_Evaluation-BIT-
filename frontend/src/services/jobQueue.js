/**
 * Job Queue Service - Handles sequential processing of student evaluations.
 * 
 * Key Features:
 * - Sequential job processing (one at a time)
 * - Status polling every 3 seconds
 * - Error handling per student (doesn't block others)
 * - Abort capability
 */
import { uploadFiles, getStatus, getResult } from './api';

// Polling interval in milliseconds
const POLL_INTERVAL = 3000;

/**
 * Sleep utility
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Map backend status/stage to frontend status
 */
function mapStatus(backendStatus, stage) {
    if (backendStatus === 'completed') return 'completed';
    if (backendStatus === 'failed') return 'failed';

    // Processing - determine sub-state from stage
    if (stage) {
        if (stage.includes('OCR') || stage.includes('EXTRACTION')) {
            return 'ocr';
        }
        if (stage.includes('EVAL') || stage.includes('SECTION')) {
            return 'evaluating';
        }
    }

    return 'ocr'; // Default to OCR if processing
}

/**
 * Process a single student job
 * @param {File} questionPaper - Question paper PDF
 * @param {File} answerKey - Answer key PDF
 * @param {File} studentFile - Student answer sheet PDF
 * @param {Function} onStatusUpdate - Callback for status updates
 * @param {AbortSignal} signal - Abort signal for cancellation
 * @returns {Object} - { success, result?, error? }
 */
export async function processStudent(
    questionPaper,
    answerKey,
    studentFile,
    onStatusUpdate,
    signal
) {
    try {
        // Check if aborted
        if (signal?.aborted) {
            return { success: false, error: 'Cancelled' };
        }

        // 1. Upload files
        onStatusUpdate({ status: 'uploading', stage: 'Uploading files...' });

        const uploadResponse = await uploadFiles(questionPaper, answerKey, studentFile);
        const jobId = uploadResponse.job_id;

        onStatusUpdate({
            status: 'ocr',
            stage: 'OCR extraction started',
            jobId
        });

        // 2. Poll for status until complete or failed
        while (true) {
            // Check if aborted
            if (signal?.aborted) {
                return { success: false, error: 'Cancelled', jobId };
            }

            await sleep(POLL_INTERVAL);

            const statusResponse = await getStatus(jobId);
            const frontendStatus = mapStatus(statusResponse.status, statusResponse.stage);

            onStatusUpdate({
                status: frontendStatus,
                stage: statusResponse.stage || frontendStatus,
                jobId,
            });

            if (statusResponse.status === 'completed') {
                // 3. Fetch result
                const result = await getResult(jobId);
                return { success: true, result, jobId };
            }

            if (statusResponse.status === 'failed') {
                return {
                    success: false,
                    error: statusResponse.error || 'Evaluation failed',
                    jobId
                };
            }
        }
    } catch (error) {
        console.error('[JobQueue] Error processing student:', error);
        return {
            success: false,
            error: error.response?.data?.detail || error.message || 'Unknown error'
        };
    }
}

/**
 * Process all students in the queue sequentially
 * @param {File} questionPaper - Question paper PDF
 * @param {File} answerKey - Answer key PDF
 * @param {File[]} studentFiles - Array of student PDFs
 * @param {Object} callbacks - { onJobStart, onJobUpdate, onJobComplete, onAllComplete }
 * @param {AbortSignal} signal - Abort signal for cancellation
 */
export async function processQueue(
    questionPaper,
    answerKey,
    studentFiles,
    callbacks,
    signal
) {
    const { onJobStart, onJobUpdate, onJobComplete, onAllComplete } = callbacks;

    for (let i = 0; i < studentFiles.length; i++) {
        // Check if aborted
        if (signal?.aborted) {
            break;
        }

        const studentFile = studentFiles[i];

        // Signal job start
        onJobStart?.(i, studentFile.name);

        // Process this student
        const result = await processStudent(
            questionPaper,
            answerKey,
            studentFile,
            (update) => onJobUpdate?.(i, update),
            signal
        );

        // Signal job complete
        onJobComplete?.(i, result);
    }

    // Signal all complete
    onAllComplete?.();
}

/**
 * Retry a single failed job
 * @param {File} questionPaper - Question paper PDF
 * @param {File} answerKey - Answer key PDF  
 * @param {File} studentFile - Student answer sheet PDF
 * @param {number} jobIndex - Index in the jobs array
 * @param {Function} onStatusUpdate - Callback for status updates
 * @returns {Object} - { success, result?, error? }
 */
export async function retryJob(
    questionPaper,
    answerKey,
    studentFile,
    jobIndex,
    onStatusUpdate
) {
    return processStudent(
        questionPaper,
        answerKey,
        studentFile,
        onStatusUpdate,
        null // No abort signal for retry
    );
}
