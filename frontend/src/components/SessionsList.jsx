import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './SessionsList.css';

const SessionsList = ({ onLoadSession, onClose }) => {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadSessions();
    }, []);

    const loadSessions = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/sessions');
            setSessions(response.data.sessions);
            setError(null);
        } catch (err) {
            console.error('Error loading sessions:', err);
            setError('Failed to load sessions');
        } finally {
            setLoading(false);
        }
    };

    const handleLoadSession = async (sessionId) => {
        try {
            const response = await axios.get(`/sessions/${sessionId}`);

            // Convert document blobs back to File objects
            const files = response.data.documents.map(doc => {
                const blob = new Blob([new Uint8Array(doc.content.data)], { type: doc.mime_type });
                return new File([blob], doc.filename, { type: doc.mime_type });
            });

            // Reconstruct the summary with bounding boxes and citations
            const summary = {
                ...response.data.summary,
                bounding_boxes: response.data.bounding_boxes,
                citations: response.data.citations,
                _token_usage: response.data._token_usage
            };

            onLoadSession(summary, files);
        } catch (err) {
            console.error('Error loading session:', err);
            setError('Failed to load session data');
        }
    };

    const handleDeleteSession = async (sessionId, event) => {
        event.stopPropagation();

        if (!window.confirm('Are you sure you want to delete this session?')) {
            return;
        }

        try {
            await axios.delete(`/sessions/${sessionId}`);
            // Reload sessions list
            loadSessions();
        } catch (err) {
            console.error('Error deleting session:', err);
            setError('Failed to delete session');
        }
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString();
    };

    return (
        <div className="sessions-overlay">
            <div className="sessions-modal">
                <div className="sessions-header">
                    <h2>Previous Sessions</h2>
                    <button onClick={onClose} className="close-btn">×</button>
                </div>

                {error && <div className="error-banner">{error}</div>}

                <div className="sessions-content">
                    {loading ? (
                        <div className="loading-spinner">Loading sessions...</div>
                    ) : sessions.length === 0 ? (
                        <div className="empty-state">
                            <p>No previous sessions found</p>
                            <p className="empty-hint">Upload and process documents to create sessions</p>
                        </div>
                    ) : (
                        <div className="sessions-list">
                            {sessions.map((session) => (
                                <div
                                    key={session.session_id}
                                    className="session-card"
                                    onClick={() => handleLoadSession(session.session_id)}
                                >
                                    <div className="session-info">
                                        <div className="session-type">{session.application_type}</div>
                                        <div className="session-date">{formatDate(session.created_at)}</div>
                                        <div className="session-id">ID: {session.session_id.substring(0, 8)}...</div>
                                    </div>
                                    <button
                                        className="delete-session-btn"
                                        onClick={(e) => handleDeleteSession(session.session_id, e)}
                                        title="Delete session"
                                    >
                                        🗑️
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="sessions-footer">
                    <button onClick={loadSessions} className="refresh-btn">
                        Refresh
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SessionsList;
