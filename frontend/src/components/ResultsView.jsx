import React from 'react';
import './ResultsView.css';

const ResultsView = ({ summary, files, onReset }) => {
    const [selectedFileIndex, setSelectedFileIndex] = React.useState(0);

    const currentFile = files && files.length > 0 ? files[selectedFileIndex] : null;
    const fileUrl = currentFile ? URL.createObjectURL(currentFile) : null;
    const isPdf = currentFile?.type === 'application/pdf';

    const flattenObject = (obj, prefix = '', rawPrefix = '') => {
        let items = [];

        for (const [key, value] of Object.entries(obj)) {
            if (key === 'source_documents' || key === '_token_usage' || key === 'citations') continue;

            const label = prefix ? `${prefix} ${key.replace(/_/g, ' ')}` : key.replace(/_/g, ' ');
            const rawKey = rawPrefix ? `${rawPrefix}.${key}` : key;

            if (value === null || value === undefined) {
                items.push({ key: label, value: '-', rawKey });
            } else if (Array.isArray(value)) {
                if (value.length === 0) {
                    items.push({ key: label, value: '-', rawKey });
                } else {
                    value.forEach((item, idx) => {
                        if (typeof item === 'object' && item !== null) {
                            const nestedItems = flattenObject(item, `${label} ${idx + 1}`, `${rawKey}[${idx}]`);
                            items = items.concat(nestedItems);
                        } else {
                            items.push({ key: `${label} ${idx + 1}`, value: String(item), rawKey: `${rawKey}[${idx}]` });
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
                    <div className="preview-content">
                        {fileUrl && (
                            isPdf ? (
                                <iframe src={fileUrl} title="Document Preview" className="preview-frame" />
                            ) : (
                                <img src={fileUrl} alt="Document Preview" className="preview-image" />
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
