import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { datasetService } from '../services/api';

const DatasetList = ({ newDataset }) => {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDatasets();
  }, [newDataset]);

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await datasetService.getAllDatasets();
      
      // Check if the response has a 'results' property (pagination)
      // or if it's already an array
      const datasetArray = Array.isArray(response) ? response : 
                          (response.results ? response.results : []);
      
      setDatasets(datasetArray);
      setLoading(false);
    } catch (err) {
      setError('Failed to load datasets');
      setLoading(false);
      console.error('Error fetching datasets:', err);
    }
  };

  if (loading) {
    return <div className="text-center py-4">Loading datasets...</div>;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  if (!datasets || datasets.length === 0) {
    return <div className="alert alert-info">No datasets available. Upload one to get started!</div>;
  }

  return (
    <div className="dataset-list">
      <h2 className="mb-4">Your Datasets</h2>
      <div className="row">
        {datasets.map(dataset => (
          <div className="col-md-4 mb-4" key={dataset.id}>
            <div className="card dataset-card h-100">
              <div className="card-body">
                <h5 className="card-title">{dataset.name}</h5>
                <p className="card-text">
                  <small className="text-muted">
                    Uploaded: {new Date(dataset.created_at).toLocaleDateString()}
                  </small>
                </p>
                <p className="card-text">
                  {dataset.tables?.length || 0} tables
                </p>
              </div>
              <div className="card-footer bg-transparent">
                <Link to={`/datasets/${dataset.id}`} className="btn btn-outline-primary me-2">
                  View Details
                </Link>
                <Link to={`/datasets/${dataset.id}/query`} className="btn btn-primary">
                  Query Data
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DatasetList;