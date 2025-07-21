import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { datasetService } from '../services/api';
import QueryForm from '../components/QueryForm';
import QueryResults from '../components/QueryResults';

const QueryPage = () => {
  const { id } = useParams();
  const [dataset, setDataset] = useState(null);
  const [queryResults, setQueryResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDataset();
  }, [id]);

  const fetchDataset = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await datasetService.getDataset(id);
      setDataset(data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load dataset');
      setLoading(false);
      console.error('Error fetching dataset:', err);
    }
  };

  const handleQuerySuccess = (results) => {
    setQueryResults(results);
    window.scrollTo({ top: document.getElementById('results-section').offsetTop, behavior: 'smooth' });
  };

  if (loading) {
    return <div className="text-center py-4">Loading dataset...</div>;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  if (!dataset) {
    return <div className="alert alert-warning">Dataset not found</div>;
  }

  return (
    <div className="query-page">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Query Dataset: {dataset.name}</h2>
        <Link to={`/datasets/${id}`} className="btn btn-outline-primary">
          Back to Dataset
        </Link>
      </div>

      <div className="row mb-4">
        <div className="col-md-12">
          <QueryForm 
            datasetId={id} 
            onQuerySuccess={handleQuerySuccess} 
          />
        </div>
      </div>

      <div id="results-section">
        <QueryResults results={queryResults} />
      </div>
    </div>
  );
};

export default QueryPage;