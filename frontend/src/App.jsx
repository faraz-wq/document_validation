import React, { useState } from 'react';
import axios from 'axios';
import UploadForm from './components/UploadForm';
import ResultsView from './components/ResultsView';

function App() {
  const [step, setStep] = useState('upload'); // upload, processing, results
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (appType, selectedFile) => {
    setStep('processing');
    setError(null);
    setFile(selectedFile);

    const formData = new FormData();
    formData.append('application_type', appType);
    formData.append('files', selectedFile);

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

  const handleReset = () => {
    setStep('upload');
    setFile(null);
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
        />
      ) : (
        <ResultsView
          summary={summary}
          file={file}
          onReset={handleReset}
        />
      )}
    </>
  );
}

export default App;
