import React, { useState, useRef } from 'react';
import './UploadForm.css';

const APPLICATION_TYPES = [
    "Income Certificate",
    "OBC Certificate",
    "EWS Certificate",
    "Integrated Certificate",
    "Family Member Certificate"
];

const UploadForm = ({ onSubmit, isLoading, error }) => {
    const [appType, setAppType] = useState('');
    const [file, setFile] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const inputRef = useRef(null);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const onButtonClick = () => {
        inputRef.current.click();
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (appType && file) {
            onSubmit(appType, file);
        }
    };

    return (
        <div className="upload-container">
            <div className="glass-card">
                <h1 className="title">Document Validation</h1>
                <p className="subtitle">Upload your certificate for instant validation and extraction.</p>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleSubmit} className="upload-form">
                    <div className="form-group">
                        <label htmlFor="appType">Application Type</label>
                        <select
                            id="appType"
                            value={appType}
                            onChange={(e) => setAppType(e.target.value)}
                            required
                            className="select-input"
                        >
                            <option value="">Select Type...</option>
                            {APPLICATION_TYPES.map(type => (
                                <option key={type} value={type}>{type}</option>
                            ))}
                        </select>
                    </div>

                    <div
                        className={`drop-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={onButtonClick}
                    >
                        <input
                            ref={inputRef}
                            type="file"
                            className="file-input"
                            onChange={handleChange}
                            accept=".pdf,image/*"
                        />
                        <div className="drop-content">
                            {file ? (
                                <div className="file-info">
                                    <span className="file-icon">📄</span>
                                    <span className="file-name">{file.name}</span>
                                    <span className="change-file">(Click to change)</span>
                                </div>
                            ) : (
                                <>
                                    <span className="upload-icon">☁️</span>
                                    <p>Drag & Drop your file here or <span className="highlight">Browse</span></p>
                                    <p className="support-text">Supports PDF, JPG, PNG</p>
                                </>
                            )}
                        </div>
                    </div>

                    <button
                        type="submit"
                        className={`submit-btn ${isLoading ? 'loading' : ''}`}
                        disabled={!appType || !file || isLoading}
                    >
                        {isLoading ? 'Processing...' : 'Validate Document'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default UploadForm;
