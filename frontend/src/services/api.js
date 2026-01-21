/**
 * API service for communicating with the backend.
 */
import axios from 'axios';

const API_BASE = '/api';

/**
 * Upload three PDF files for evaluation.
 * @param {File} questionPaper - Question paper PDF
 * @param {File} answerKey - Answer key PDF
 * @param {File} studentSheet - Student answer sheet PDF
 * @returns {Promise<{job_id: string, status: string}>}
 */
export async function uploadFiles(questionPaper, answerKey, studentSheet) {
    const formData = new FormData();
    formData.append('question_paper', questionPaper);
    formData.append('answer_key', answerKey);
    formData.append('student_sheet', studentSheet);

    const response = await axios.post(`${API_BASE}/upload`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });

    return response.data;
}

/**
 * Get the status of an evaluation job.
 * @param {string} jobId - Job ID from upload
 * @returns {Promise<{job_id: string, status: string, error?: string}>}
 */
export async function getStatus(jobId) {
    const response = await axios.get(`${API_BASE}/status/${jobId}`);
    return response.data;
}

/**
 * Get the evaluation result for a completed job.
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} - Evaluation result JSON
 */
export async function getResult(jobId) {
    const response = await axios.get(`${API_BASE}/result/${jobId}`);
    return response.data;
}
