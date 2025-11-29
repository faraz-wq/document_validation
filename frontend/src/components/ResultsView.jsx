import React from 'react';
import './ResultsView.css';

const ResultsView = ({ summary, file, onReset }) => {
    const fileUrl = file ? URL.createObjectURL(file) : null;
    const isPdf = file?.type === 'application/pdf';

    const flattenObject = (obj, prefix = '') => {
        let items = [];

        for (const [key, value] of Object.entries(obj)) {
            if (key === 'source_documents' || key === '_token_usage') continue;

            const label = prefix ? `${prefix} ${key.replace(/_/g, ' ')}` : key.replace(/_/g, ' ');

            if (value === null || value === undefined) {
                items.push({ key: label, value: '-' });
            } else if (Array.isArray(value)) {
                if (value.length === 0) {
                    items.push({ key: label, value: '-' });
                } else {
                    value.forEach((item, idx) => {
                        if (typeof item === 'object' && item !== null) {
                            const nestedItems = flattenObject(item, `${label} ${idx + 1}`);
                            items = items.concat(nestedItems);
                        } else {
                            items.push({ key: `${label} ${idx + 1}`, value: String(item) });
                        }
                    });
                }
            } else if (typeof value === 'object') {
                const nestedItems = flattenObject(value, label);
                items = items.concat(nestedItems);
            } else {
                items.push({ key: label, value: String(value) });
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
                    <div className="panel-header">Document Preview</div>
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
                                            <td className="value-cell">{item.value}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            <table className="summary-table">
                                <tbody>
                                    {rightColumn.map((item, idx) => (
                                        <tr key={idx}>
                                            <td className="key-cell">{item.key}</td>
                                            <td className="value-cell">{item.value}</td>
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
