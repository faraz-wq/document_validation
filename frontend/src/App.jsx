import React, { useState } from 'react';
import axios from 'axios';
import UploadForm from './components/UploadForm';
import ResultsView from './components/ResultsView';
import SessionsList from './components/SessionsList';

function App() {
  const [step, setStep] = useState('upload'); // upload, processing, results
  const [files, setFiles] = useState([]);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [showSessions, setShowSessions] = useState(false);

  const handleUpload = async (appType, selectedFiles) => {
    setStep('processing');
    setError(null);
    setFiles(selectedFiles);

    const formData = new FormData();
    formData.append('application_type', appType);

    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      // Using relative path - Vite proxy will forward to localhost:8000
      const response = await axios.post('/extract-summary', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSummary(response.data);
      setStep('results');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred during processing.');
      setStep('upload');
    }
  };

  const handleLoadSession = (sessionSummary, sessionFiles) => {
    setSummary(sessionSummary);
    setFiles(sessionFiles);
    setStep('results');
    setShowSessions(false);
  };

  const handleReset = () => {
    setStep('upload');
    setFiles([]);
    setSummary(null);
    setError(null);
  };

  return (
    <>
      {step === 'upload' || step === 'processing' ? (
        <UploadForm
          onSubmit={handleUpload}
          isLoading={step === 'processing'}
          error={error}
          onShowSessions={() => setShowSessions(true)}
        />
      ) : (
        <ResultsView
          summary={summary}
          files={files}
          onReset={handleReset}
        />
      )}

      {showSessions && (
        <SessionsList
          onLoadSession={handleLoadSession}
          onClose={() => setShowSessions(false)}
        />
      )}
    </>
  );
}

export default App;
