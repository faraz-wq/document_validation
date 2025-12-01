import React, { useRef, useEffect, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Set up the worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const PDFViewerWithBoxes = ({ fileUrl, boundingBox, onLoadDimensions }) => {
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [pageWidth, setPageWidth] = useState(0);
    const [pageHeight, setPageHeight] = useState(0);
    const canvasRef = useRef(null);
    const containerRef = useRef(null);

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
    };

    const onPageLoadSuccess = (page) => {
        const { width, height } = page;
        setPageWidth(width);
        setPageHeight(height);

        if (onLoadDimensions) {
            onLoadDimensions({ width, height });
        }
    };

    // Draw bounding box on canvas overlay
    useEffect(() => {
        if (!boundingBox || !canvasRef.current || !pageWidth || !pageHeight) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        // Clear previous drawings
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Only draw if this is the correct page
        if (boundingBox.page !== pageNumber) return;

        const [y_min, x_min, y_max, x_max] = boundingBox.coordinates;

        // Convert normalized coordinates (0-1000) to canvas coordinates
        const scaleX = canvas.width / 1000;
        const scaleY = canvas.height / 1000;

        const x = x_min * scaleX;
        const y = y_min * scaleY;
        const width = (x_max - x_min) * scaleX;
        const height = (y_max - y_min) * scaleY;

        // Draw bounding box
        ctx.strokeStyle = '#ff6b6b';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        // Fill with semi-transparent color
        ctx.fillStyle = 'rgba(255, 107, 107, 0.2)';
        ctx.fillRect(x, y, width, height);
    }, [boundingBox, pageNumber, pageWidth, pageHeight]);

    // Update page number if bounding box changes
    useEffect(() => {
        if (boundingBox && boundingBox.page) {
            setPageNumber(boundingBox.page);
        }
    }, [boundingBox]);

    return (
        <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%' }}>
            <Document
                file={fileUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={<div>Loading PDF...</div>}
            >
                <Page
                    pageNumber={pageNumber}
                    onLoadSuccess={onPageLoadSuccess}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                    width={pageWidth || undefined}
                    height={pageHeight || undefined}
                />
            </Document>

            {/* Canvas overlay for bounding boxes */}
            <canvas
                ref={canvasRef}
                width={pageWidth || 0}
                height={pageHeight || 0}
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    pointerEvents: 'none',
                    zIndex: 10
                }}
            />

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
    );
};

export default PDFViewerWithBoxes;
