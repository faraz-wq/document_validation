import React from 'react';
import './ResultsView.css';

const ResultsView = ({ summary, files, onReset }) => {
    const [selectedFileIndex, setSelectedFileIndex] = React.useState(0);
    const [hoveredField, setHoveredField] = React.useState(null);
    const [documentDimensions, setDocumentDimensions] = React.useState({ width: 0, height: 0 });
    const previewRef = React.useRef(null);

    const currentFile = files && files.length > 0 ? files[selectedFileIndex] : null;
    const isPdf = currentFile?.type === 'application/pdf';

    // Memoize blob URL creation to prevent recreating on every render
    const fileUrl = React.useMemo(() => {
        if (!currentFile) return null;
        return URL.createObjectURL(currentFile);
    }, [currentFile]);

    // Cleanup blob URL when component unmounts or file changes
    React.useEffect(() => {
        return () => {
            if (fileUrl) {
                URL.revokeObjectURL(fileUrl);
            }
        };
    }, [fileUrl]);

    // Get bounding box for the currently hovered field
    const activeBoundingBox = hoveredField && summary?.bounding_boxes?.[hoveredField];

    // Handle image/iframe load to get dimensions
    const handlePreviewLoad = (e) => {
        if (isPdf && e.target.tagName === 'IFRAME') {
            // For PDFs, use the iframe dimensions
            setDocumentDimensions({
                width: e.target.offsetWidth,
                height: e.target.offsetHeight
            });
        } else if (e.target.tagName === 'IMG') {
            // For images, use natural dimensions
            setDocumentDimensions({
                width: e.target.naturalWidth,
                height: e.target.naturalHeight
            });
        }
    };

    // Convert normalized coordinates (0-1000) to actual pixel coordinates
    const getBoundingBoxStyle = (bbox) => {
        if (!bbox || !documentDimensions.width || !documentDimensions.height) return null;

        const [y_min, x_min, y_max, x_max] = bbox.coordinates;

        // Convert from 1000x1000 normalized space to actual dimensions
        const left = (x_min / 1000) * documentDimensions.width;
        const top = (y_min / 1000) * documentDimensions.height;
        const width = ((x_max - x_min) / 1000) * documentDimensions.width;
        const height = ((y_max - y_min) / 1000) * documentDimensions.height;

        return {
            position: 'absolute',
            left: `${left}px`,
            top: `${top}px`,
            width: `${width}px`,
            height: `${height}px`,
            border: '2px solid #ff6b6b',
            backgroundColor: 'rgba(255, 107, 107, 0.2)',
            pointerEvents: 'none',
            zIndex: 10,
            transition: 'all 0.2s ease'
        };
    };

    const flattenObject = (obj, prefix = '', rawPrefix = '') => {
        let items = [];

        for (const [key, value] of Object.entries(obj)) {
            if (key === 'source_documents' || key === '_token_usage' || key === 'citations') continue;

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
                        Document Preview
                        {files && files.length > 1 && (
                            <div className="file-selector">
                                <select
                                    value={selectedFileIndex}
                                    onChange={(e) => setSelectedFileIndex(Number(e.target.value))}
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
                    <div className="preview-content" ref={previewRef}>
                        {fileUrl && (
                            <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                {isPdf ? (
                                    <iframe
                                        src={fileUrl}
                                        title="Document Preview"
                                        className="preview-frame"
                                        onLoad={handlePreviewLoad}
                                    />
                                ) : (
                                    <img
                                        src={fileUrl}
                                        alt="Document Preview"
                                        className="preview-image"
                                        onLoad={handlePreviewLoad}
                                    />
                                )}
                                {activeBoundingBox && activeBoundingBox.filename === currentFile?.name && (
                                    <div style={getBoundingBoxStyle(activeBoundingBox)} className="bounding-box-highlight" />
                                )}
                            </div>
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
                                        <tr
                                            key={idx}
                                            onMouseEnter={() => setHoveredField(item.rawKey)}
                                            onMouseLeave={() => setHoveredField(null)}
                                            className={hoveredField === item.rawKey ? 'highlighted-row' : ''}
                                        >
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
                                        <tr
                                            key={idx}
                                            onMouseEnter={() => setHoveredField(item.rawKey)}
                                            onMouseLeave={() => setHoveredField(null)}
                                            className={hoveredField === item.rawKey ? 'highlighted-row' : ''}
                                        >
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
