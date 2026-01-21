/**
 * MasterFileUpload - Upload single Question Paper and Answer Key.
 * These files are cached and reused for all student evaluations.
 */
import React, { useRef, useState } from 'react';
import { useEvaluation } from '../context/EvaluationContext';

const FILE_TYPES = [
    { key: 'questionPaper', label: 'Question Paper', icon: '📄', description: 'Upload the exam question paper' },
    { key: 'answerKey', label: 'Answer Key', icon: '✓', description: 'Upload the official answer key' },
];

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function MasterFileUpload({ disabled }) {
    const { state, actions } = useEvaluation();
    const fileInputRefs = useRef({});
    const [dragOver, setDragOver] = useState(null);

    const handleFileSelect = (key, file) => {
        if (file && file.type === 'application/pdf') {
            actions.setMasterFile(key, file);
        }
    };

    const handleDrop = (key, e) => {
        e.preventDefault();
        setDragOver(null);
        const file = e.dataTransfer.files[0];
        handleFileSelect(key, file);
    };

    const removeFile = (key) => {
        actions.setMasterFile(key, null);
    };

    return (
        <div className="master-upload-section">
            <h3 className="section-title">
                <span className="section-icon">📋</span>
                Master Documents
            </h3>
            <p className="section-description">
                Upload once — reused for all student evaluations
            </p>

            <div className="master-files-grid">
                {FILE_TYPES.map(({ key, label, icon, description }) => (
                    <div key={key} className="master-file-card">
                        {state.masterFiles[key] ? (
                            <div className="file-uploaded">
                                <div className="file-icon-large">{icon}</div>
                                <div className="file-details">
                                    <div className="file-label">{label}</div>
                                    <div className="file-name">{state.masterFiles[key].name}</div>
                                    <div className="file-size">{formatFileSize(state.masterFiles[key].size)}</div>
                                </div>
                                <button
                                    className="remove-btn"
                                    onClick={() => removeFile(key)}
                                    disabled={disabled}
                                    title="Remove file"
                                >
                                    ✕
                                </button>
                            </div>
                        ) : (
                            <div
                                className={`upload-zone-master ${dragOver === key ? 'drag-over' : ''}`}
                                onClick={() => fileInputRefs.current[key]?.click()}
                                onDrop={(e) => handleDrop(key, e)}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(key); }}
                                onDragLeave={() => setDragOver(null)}
                            >
                                <div className="upload-icon">{icon}</div>
                                <div className="upload-label">{label}</div>
                                <div className="upload-hint">{description}</div>
                                <input
                                    ref={(el) => (fileInputRefs.current[key] = el)}
                                    type="file"
                                    accept=".pdf"
                                    hidden
                                    onChange={(e) => handleFileSelect(key, e.target.files[0])}
                                    disabled={disabled}
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
