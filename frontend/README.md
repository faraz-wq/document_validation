# Document Validation Frontend

A modern React application for document validation and extraction.

## Features

- 🎨 Beautiful dark mode UI with glassmorphism effects
- 📤 Drag & drop file upload
- 📄 Support for PDF and image documents
- ⚡ Real-time document processing
- 📊 Split-screen results view with document preview

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- Backend service running on port 8000

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The application will start on `http://localhost:3000`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── UploadForm.jsx       # Upload interface with drag & drop
│   ├── UploadForm.css
│   ├── ResultsView.jsx      # Results display with split view
│   └── ResultsView.css
├── App.jsx                  # Main application component
├── index.css                # Global styles and design tokens
└── main.jsx                 # Application entry point
```

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`:

- `POST /extract-summary` - Submit documents for validation and extraction

## Technologies

- **React** - UI framework
- **Vite** - Build tool and dev server
- **Axios** - HTTP client
- **CSS3** - Styling with modern features (glassmorphism, gradients)
