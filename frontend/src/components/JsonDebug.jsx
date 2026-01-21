import React, { useState } from 'react';

export default function JsonDebug({ data }) {
    const [isOpen, setIsOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    if (!data) return null;

    const jsonString = JSON.stringify(data, null, 2);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(jsonString);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    return (
        <div className="json-debug">
            <button className="json-toggle" onClick={() => setIsOpen(!isOpen)}>
                <span>{isOpen ? '▼' : '▶'}</span>
                <span>View Raw JSON Response</span>
            </button>

            {isOpen && (
                <div className="json-content">
                    <pre>{jsonString}</pre>
                    <button className="json-copy-btn" onClick={handleCopy}>
                        {copied ? '✓ Copied!' : '📋 Copy to Clipboard'}
                    </button>
                </div>
            )}
        </div>
    );
}
