import React, { useState } from 'react';
import { datasetService } from '../services/api';

const FileUploader = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    try {
      setIsUploading(true);
      setError('');

      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', fileName);

      // Determine file type from extension
      const fileExtension = file.name.split('.').pop().toLowerCase();
      formData.append('file_type', fileExtension === 'csv' ? 'csv' : 'xlsx');

      const result = await datasetService.uploadDataset(formData);
      
      setIsUploading(false);
      setFile(null);
      setFileName('');
      
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      setIsUploading(false);
      setError(err.response?.data?.error || 'Failed to upload file. Please try again.');
      console.error('Upload error:', err);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">Upload Dataset</h5>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          <div className="upload-area mb-3">
            <input
              type="file"
              className="form-control"
              id="fileInput"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileChange}
            />
            <small className="text-muted d-block mt-2">
              Supported file types: CSV and Excel (.xlsx, .xls)
            </small>
          </div>

          <div className="mb-3">
            <label htmlFor="fileName" className="form-label">Dataset Name</label>
            <input
              type="text"
              className="form-control"
              id="fileName"
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
              placeholder="Enter a name for this dataset"
              required
            />
          </div>

          {error && <div className="alert alert-danger">{error}</div>}

          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={isUploading || !file}
          >
            {isUploading ? 'Uploading...' : 'Upload Dataset'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default FileUploader;