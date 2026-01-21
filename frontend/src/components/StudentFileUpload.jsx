/**
 * StudentFileUpload - Multi-file upload for student answer sheets.
 * Maximum 40 files, 25MB per file (displayed limit).
 */
import React, { useRef, useState } from 'react';
import { useEvaluation } from '../context/EvaluationContext';

const MAX_FILES = 40;
const MAX_FILE_SIZE_MB = 25; // Displayed limit (actual is 50MB)
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // Actual limit

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function StudentFileUpload({ disabled }) {
    const { state, actions } = useEvaluation();
    const fileInputRef = useRef(null);
    const [dragOver, setDragOver] = useState(false);
    const [error, setError] = useState(null);

    const handleFilesSelect = (files) => {
        setError(null);
        const validFiles = [];

        for (const file of Array.from(files)) {
            // Check file type
            if (file.type !== 'application/pdf') {
                setError(`"${file.name}" is not a PDF file`);
                continue;
            }

            // Check file size
            if (file.size > MAX_FILE_SIZE_BYTES) {
                setError(`"${file.name}" exceeds ${MAX_FILE_SIZE_MB}MB limit`);
                continue;
            }

            validFiles.push(file);
        }

        // Check total count
        const remaining = MAX_FILES - state.studentFiles.length;
        if (validFiles.length > remaining) {
            setError(`Maximum ${MAX_FILES} files allowed. Only first ${remaining} files added.`);
            validFiles.splice(remaining);
        }

        if (validFiles.length > 0) {
            actions.addStudentFiles(validFiles);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        handleFilesSelect(e.dataTransfer.files);
    };

    const removeFile = (index) => {
        actions.removeStudentFile(index);
        setError(null);
    };

    return (
        <div className="student-upload-section">
            <h3 className="section-title">
                <span className="section-icon">✍️</span>
                Student Answer Sheets
                <span className="file-count">
                    {state.studentFiles.length} / {MAX_FILES}
                </span>
            </h3>
            <p className="section-description">
                Upload multiple student papers for batch evaluation
            </p>

            {/* Upload Zone */}
            <div
                className={`upload-zone-multi ${dragOver ? 'drag-over' : ''} ${disabled ? 'disabled' : ''}`}
                onClick={() => !disabled && fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
            >
                <div className="upload-icon-large">📁</div>
                <div className="upload-text">
                    <strong>Click to upload</strong> or drag and drop
                </div>
                <div className="upload-hint">
                    PDF files only • Max {MAX_FILE_SIZE_MB}MB per file • Up to {MAX_FILES} files
                </div>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    multiple
                    hidden
                    onChange={(e) => handleFilesSelect(e.target.files)}
                    disabled={disabled}
                />
            </div>

            {/* Error message */}
            {error && (
                <div className="upload-error">
                    <span className="error-icon">⚠️</span>
                    {error}
                </div>
            )}

            {/* File list */}
            {state.studentFiles.length > 0 && (
                <div className="student-files-list">
                    {state.studentFiles.map((file, index) => (
                        <div key={`${file.name}-${index}`} className="student-file-item">
                            <div className="file-info">
                                <span className="file-number">{index + 1}</span>
                                <span className="file-name">{file.name}</span>
                                <span className="file-size">{formatFileSize(file.size)}</span>
                            </div>
                            <button
                                className="remove-btn-small"
                                onClick={() => removeFile(index)}
                                disabled={disabled}
                                title="Remove file"
                            >
                                ✕
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
