import { useState, useRef, useCallback } from 'react';
import { Upload as UploadIcon, FileText, Loader, CheckCircle, XCircle } from 'lucide-react';
import { uploadPDFs } from '../services/api';
import type { UploadResponse } from '../services/api';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return;
    const pdfFiles = Array.from(newFiles).filter(
      (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
    );
    setFiles((prev) => [...prev, ...pdfFiles]);
    setUploadState('idle');
    setResult(null);
    setErrorMessage('');
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploadState('uploading');
    setErrorMessage('');
    try {
      const response = await uploadPDFs(files);
      setResult(response);
      setUploadState('success');
      setFiles([]);
    } catch (err: unknown) {
      setUploadState('error');
      if (err instanceof Error) {
        setErrorMessage(err.message || 'Upload failed. Please try again.');
      } else {
        setErrorMessage('Upload failed. Please try again.');
      }
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-4 max-w-lg mx-auto">
      {/* Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragOver
            ? 'border-green-500 bg-green-50'
            : 'border-gray-300 bg-white'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
      >
        <UploadIcon className="w-12 h-12 mx-auto mb-3 text-gray-400" />
        <p className="text-base font-medium text-gray-700">
          Drop PDF files here
        </p>
        <p className="text-sm text-gray-500 mt-1">or tap to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="text-sm font-medium text-gray-700">
            Selected Files ({files.length})
          </h3>
          {files.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between bg-white rounded-lg p-3 border border-gray-200"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-5 h-5 text-green-600 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(index);
                }}
                className="text-gray-400 hover:text-red-500 p-1"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload Button */}
      {files.length > 0 && uploadState !== 'uploading' && (
        <button
          onClick={handleUpload}
          className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg text-base transition-colors"
        >
          Upload {files.length} {files.length === 1 ? 'File' : 'Files'}
        </button>
      )}

      {/* Uploading State */}
      {uploadState === 'uploading' && (
        <div className="mt-4 flex items-center justify-center gap-2 text-green-600">
          <Loader className="w-5 h-5 animate-spin" />
          <span className="text-sm font-medium">Processing PDFs...</span>
        </div>
      )}

      {/* Success State */}
      {uploadState === 'success' && result && (
        <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-green-700 mb-2">
            <CheckCircle className="w-5 h-5" />
            <span className="font-semibold">Upload Complete</span>
          </div>
          <p className="text-sm text-green-800">
            {result.documents.length} document{result.documents.length !== 1 ? 's' : ''} processed successfully.
          </p>
          <p className="text-sm text-green-700 mt-1">{result.message}</p>
        </div>
      )}

      {/* Error State */}
      {uploadState === 'error' && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700">
            <XCircle className="w-5 h-5" />
            <span className="font-semibold">Upload Failed</span>
          </div>
          <p className="text-sm text-red-600 mt-1">{errorMessage}</p>
        </div>
      )}
    </div>
  );
}
