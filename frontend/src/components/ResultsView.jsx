import React from 'react';
import './ResultsView.css';
import { Document, Page, pdfjs } from 'react-pdf';

// Set up the worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const ResultsView = ({ summary, files, onReset }) => {
    const [selectedFileIndex, setSelectedFileIndex] = React.useState(0);
    const [numPages, setNumPages] = React.useState(null);
    const [pageNumber, setPageNumber] = React.useState(1);

    // Check if we have annotated files from the backend
    const annotatedFiles = summary?.annotated_files || [];
    const hasAnnotatedFiles = annotatedFiles.length > 0;

    // Use annotated file if available, otherwise use original
    const currentFile = files && files.length > 0 ? files[selectedFileIndex] : null;
    const currentAnnotatedFile = hasAnnotatedFiles ? annotatedFiles[selectedFileIndex] : null;

    // Determine if we should show the annotated version
    const useAnnotated = hasAnnotatedFiles && currentAnnotatedFile;

    // Create file URL - use annotated if available
    const fileUrl = React.useMemo(() => {
        if (useAnnotated) {
            // Use the annotated file URL from the backend
            return currentAnnotatedFile.annotated_url;
        }

        if (currentFile) {
            // If it's a File object (fresh upload)
            if (currentFile instanceof File) {
                return URL.createObjectURL(currentFile);
            }
            // If it has a url property (e.g. from session)
            if (currentFile.url) {
                return currentFile.url;
            }
        }
        return null;
    }, [currentFile, currentAnnotatedFile, useAnnotated]);

    // Cleanup blob URL when component unmounts or file changes (only for blob URLs)
    React.useEffect(() => {
        return () => {
            if (fileUrl && fileUrl.startsWith('blob:')) {
                URL.revokeObjectURL(fileUrl);
            }
        };
    }, [fileUrl]);

    // Determine file type
    const isPdf = currentFile?.type === 'application/pdf' || useAnnotated; // Annotated files are always PDFs

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
    };

    // Configure PDF loading options
    const pdfOptions = React.useMemo(() => {
        if (useAnnotated && fileUrl && !fileUrl.startsWith('blob:')) {
            // For server URLs, configure proper loading
            return {
                url: fileUrl,
                httpHeaders: {
                    'Accept': 'application/pdf',
                },
                withCredentials: false,
            };
        }
        // For blob URLs, just return the URL
        return fileUrl;
    }, [fileUrl, useAnnotated]);

    const flattenObject = (obj, prefix = '', rawPrefix = '') => {
        let items = [];

        for (const [key, value] of Object.entries(obj)) {
            if (key === 'source_documents' || key === '_token_usage' || key === 'citations' || key === 'bounding_boxes' || key === 'annotated_files') continue;

            const label = prefix ? `${prefix} ${key.replace(/_/g, ' ')} ` : key.replace(/_/g, ' ');
            const rawKey = rawPrefix ? `${rawPrefix}.${key} ` : key;

            if (value === null || value === undefined) {
                items.push({ key: label, value: '-', rawKey });
            } else if (Array.isArray(value)) {
                if (value.length === 0) {
                    items.push({ key: label, value: '-', rawKey });
                } else {
                    value.forEach((item, idx) => {
                        if (typeof item === 'object' && item !== null) {
                            const nestedItems = flattenObject(item, `${label} ${idx + 1} `, `${rawKey} [${idx}]`);
                            items = items.concat(nestedItems);
                        } else {
                            items.push({ key: `${label} ${idx + 1} `, value: String(item), rawKey: `${rawKey} [${idx}]` });
                        }
                    });
                }
            } else if (typeof value === 'object') {
                const nestedItems = flattenObject(value, label, rawKey);
                items = items.concat(nestedItems);
            } else {
                items.push({ key: label, value: String(value), rawKey });
            }
        }

        return items;
    };

    const allFields = summary ? flattenObject(summary) : [];
    const midpoint = Math.ceil(allFields.length / 2);
    const leftColumn = allFields.slice(0, midpoint);
    const rightColumn = allFields.slice(midpoint);

    // Extract token usage if available
    const tokenUsage = summary?._token_usage;

    return (
        <div className="results-container">
            <div className="results-header">
                <h2 className="results-title">Validation Results</h2>
                <div className="header-actions">
                    {tokenUsage && tokenUsage.total_token_count && (
                        <div className="token-counter">
                            <span className="token-label">Tokens:</span>
                            <span className="token-value">{tokenUsage.total_token_count.toLocaleString()}</span>
                            <span className="token-detail">
                                (↑{tokenUsage.prompt_token_count.toLocaleString()}
                                ↓{tokenUsage.candidates_token_count.toLocaleString()})
                            </span>
                        </div>
                    )}
                    <button onClick={onReset} className="reset-btn">
                        Upload New Document
                    </button>
                </div>
            </div>

            <div className="split-view">
                <div className="preview-panel">
                    <div className="panel-header">
                        Document Preview {useAnnotated && <span style={{ color: '#4CAF50', fontSize: '0.9em' }}>(Annotated)</span>}
                        {files && files.length > 1 && (
                            <div className="file-selector">
                                <select
                                    value={selectedFileIndex}
                                    onChange={(e) => {
                                        setSelectedFileIndex(Number(e.target.value));
                                        setPageNumber(1); // Reset to first page when changing files
                                    }}
                                    className="file-select"
                                >
                                    {files.map((f, idx) => (
                                        <option key={idx} value={idx}>
                                            {f.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>
                    <div className="preview-content">
                        {fileUrl && (
                            isPdf ? (
                                <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                                    <Document
                                        file={pdfOptions}
                                        onLoadSuccess={onDocumentLoadSuccess}
                                        loading={<div>Loading PDF...</div>}
                                    >
                                        <Page
                                            pageNumber={pageNumber}
                                            renderTextLayer={true}
                                            renderAnnotationLayer={true}
                                            width={800}
                                        />
                                    </Document>

                                    {/* Page navigation */}
                                    {numPages && numPages > 1 && (
                                        <div style={{
                                            position: 'absolute',
                                            bottom: '10px',
                                            left: '50%',
                                            transform: 'translateX(-50%)',
                                            background: 'rgba(0, 0, 0, 0.7)',
                                            color: 'white',
                                            padding: '8px 16px',
                                            borderRadius: '4px',
                                            display: 'flex',
                                            gap: '10px',
                                            alignItems: 'center'
                                        }}>
                                            <button
                                                onClick={() => setPageNumber(prev => Math.max(1, prev - 1))}
                                                disabled={pageNumber <= 1}
                                                style={{
                                                    background: 'transparent',
                                                    border: '1px solid white',
                                                    color: 'white',
                                                    padding: '4px 8px',
                                                    cursor: pageNumber <= 1 ? 'not-allowed' : 'pointer',
                                                    opacity: pageNumber <= 1 ? 0.5 : 1
                                                }}
                                            >
                                                ←
                                            </button>
                                            <span>
                                                Page {pageNumber} of {numPages}
                                            </span>
                                            <button
                                                onClick={() => setPageNumber(prev => Math.min(numPages, prev + 1))}
                                                disabled={pageNumber >= numPages}
                                                style={{
                                                    background: 'transparent',
                                                    border: '1px solid white',
                                                    color: 'white',
                                                    padding: '4px 8px',
                                                    cursor: pageNumber >= numPages ? 'not-allowed' : 'pointer',
                                                    opacity: pageNumber >= numPages ? 0.5 : 1
                                                }}
                                            >
                                                →
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <img
                                        src={fileUrl}
                                        alt="Document Preview"
                                        className="preview-image"
                                    />
                                </div>
                            )
                        )}
                    </div>
                </div>

                <div className="summary-panel">
                    <div className="panel-header">Extraction Summary</div>
                    <div className="summary-content">
                        <div className="summary-columns">
                            <table className="summary-table">
                                <tbody>
                                    {leftColumn.map((item, idx) => (
                                        <tr key={idx}>
                                            <td className="key-cell">{item.key}</td>
                                            <td className="value-cell">
                                                {item.value}
                                                {summary.citations && summary.citations[item.rawKey] && (
                                                    <div className="citation-text">
                                                        Source: {summary.citations[item.rawKey]}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            <table className="summary-table">
                                <tbody>
                                    {rightColumn.map((item, idx) => (
                                        <tr key={idx}>
                                            <td className="key-cell">{item.key}</td>
                                            <td className="value-cell">
                                                {item.value}
                                                {summary.citations && summary.citations[item.rawKey] && (
                                                    <div className="citation-text">
                                                        Source: {summary.citations[item.rawKey]}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResultsView;
