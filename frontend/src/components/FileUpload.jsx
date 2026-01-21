import React, { useRef, useState } from 'react';

const FILE_TYPES = [
    { key: 'questionPaper', label: 'Question Paper', icon: '📄' },
    { key: 'answerKey', label: 'Answer Key', icon: '✓' },
    { key: 'studentSheet', label: 'Student Answer Sheet', icon: '✍️' },
];

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function FileUpload({ files, onFilesChange, disabled }) {
    const fileInputRefs = useRef({});
    const [dragOver, setDragOver] = useState(null);

    const handleFileSelect = (key, file) => {
        if (file && file.type === 'application/pdf') {
            onFilesChange({ ...files, [key]: file });
        }
    };

    const handleDrop = (key, e) => {
        e.preventDefault();
        setDragOver(null);
        const file = e.dataTransfer.files[0];
        handleFileSelect(key, file);
    };

    const handleDragOver = (key, e) => {
        e.preventDefault();
        setDragOver(key);
    };

    const handleDragLeave = () => {
        setDragOver(null);
    };

    const removeFile = (key) => {
        const newFiles = { ...files };
        delete newFiles[key];
        onFilesChange(newFiles);
    };

    return (
        <div className="card">
            <h3 className="card-title">
                <span className="icon">📎</span>
                Upload Exam Documents
            </h3>

            <div className="file-list">
                {FILE_TYPES.map(({ key, label, icon }) => (
                    <div key={key}>
                        {files[key] ? (
                            <div className="file-item">
                                <div className="file-info">
                                    <div className="file-icon">{icon}</div>
                                    <div>
                                        <div className="file-name">{label}</div>
                                        <div className="file-size">
                                            {files[key].name} • {formatFileSize(files[key].size)}
                                        </div>
                                    </div>
                                </div>
                                <button
                                    className="remove-btn"
                                    onClick={() => removeFile(key)}
                                    disabled={disabled}
                                >
                                    ✕
                                </button>
                            </div>
                        ) : (
                            <div
                                className={`upload-zone ${dragOver === key ? 'drag-over' : ''}`}
                                onClick={() => fileInputRefs.current[key]?.click()}
                                onDrop={(e) => handleDrop(key, e)}
                                onDragOver={(e) => handleDragOver(key, e)}
                                onDragLeave={handleDragLeave}
                            >
                                <div className="icon">{icon}</div>
                                <h3>{label}</h3>
                                <p>Click to browse or drag & drop PDF file</p>
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
