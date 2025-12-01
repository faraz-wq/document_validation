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
    const [files, setFiles] = useState([]);
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
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            setFiles(Array.from(e.dataTransfer.files));
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files.length > 0) {
            setFiles(Array.from(e.target.files));
        }
    };

    const onButtonClick = () => {
        inputRef.current.click();
    };

    const removeFile = (index, e) => {
        e.stopPropagation();
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (appType && files.length > 0) {
            onSubmit(appType, files);
        }
    };

    return (
        <div className="upload-container">
            <div className="glass-card">
                <h1 className="title">Document Validation</h1>
                <p className="subtitle">Upload your certificates for instant validation and extraction.</p>

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
                        className={`drop-zone ${dragActive ? 'drag-active' : ''} ${files.length > 0 ? 'has-file' : ''}`}
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
                            multiple
                        />
                        <div className="drop-content">
                            {files.length > 0 ? (
                                <div className="file-list">
                                    {files.map((file, index) => (
                                        <div key={index} className="file-info-item">
                                            <span className="file-icon">📄</span>
                                            <span className="file-name">{file.name}</span>
                                            <button
                                                type="button"
                                                className="remove-file-btn"
                                                onClick={(e) => removeFile(index, e)}
                                            >
                                                ×
                                            </button>
                                        </div>
                                    ))}
                                    <div className="add-more-hint">(Click to add/change files)</div>
                                </div>
                            ) : (
                                <>
                                    <span className="upload-icon">☁️</span>
                                    <p>Drag & Drop your files here or <span className="highlight">Browse</span></p>
                                    <p className="support-text">Supports PDF, JPG, PNG (Multiple files allowed)</p>
                                </>
                            )}
                        </div>
                    </div>

                    <button
                        type="submit"
                        className={`submit-btn ${isLoading ? 'loading' : ''}`}
                        disabled={!appType || files.length === 0 || isLoading}
                    >
                        {isLoading ? 'Processing...' : `Validate ${files.length > 0 ? `${files.length} Document${files.length > 1 ? 's' : ''}` : 'Document'}`}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default UploadForm;
