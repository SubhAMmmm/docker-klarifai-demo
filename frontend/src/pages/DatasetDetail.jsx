import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { datasetService } from '../services/api';

const DatasetDetail = () => {
  const { id } = useParams();
  const [dataset, setDataset] = useState(null);
  const [tables, setTables] = useState([]);
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('tables');

  useEffect(() => {
    fetchDatasetDetails();
  }, [id]);

  const fetchDatasetDetails = async () => {
    try {
      setLoading(true);
      setError('');

      // Fetch dataset details
      const datasetData = await datasetService.getDataset(id);
      setDataset(datasetData);

      // Fetch tables
      const tablesData = await datasetService.getDatasetTables(id);
      setTables(tablesData);

      // Fetch schema
      const schemaData = await datasetService.getDatasetSchema(id);
      setSchema(schemaData);

      setLoading(false);
    } catch (err) {
      setError('Failed to load dataset details');
      setLoading(false);
      console.error('Error fetching dataset details:', err);
    }
  };

  if (loading) {
    return <div className="text-center py-4">Loading dataset details...</div>;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  if (!dataset) {
    return <div className="alert alert-warning">Dataset not found</div>;
  }

  return (
    <div className="dataset-detail">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{dataset.name}</h2>
        <Link to={`/datasets/${id}/query`} className="btn btn-primary">
          Query This Dataset
        </Link>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <div className="row">
            <div className="col-md-6">
              <p><strong>File type:</strong> {dataset.file_type.toUpperCase()}</p>
              <p><strong>Uploaded:</strong> {new Date(dataset.created_at).toLocaleString()}</p>
            </div>
            <div className="col-md-6">
              <p><strong>Tables:</strong> {tables.length}</p>
              <p><strong>File:</strong> {dataset.file.split('/').pop()}</p>
            </div>
          </div>
        </div>
      </div>

      <ul className="nav nav-tabs mb-4">
        <li className="nav-item">
          <button 
            className={`nav-link ${activeTab === 'tables' ? 'active' : ''}`}
            onClick={() => setActiveTab('tables')}
          >
            Tables
          </button>
        </li>
        <li className="nav-item">
          <button 
            className={`nav-link ${activeTab === 'schema' ? 'active' : ''}`}
            onClick={() => setActiveTab('schema')}
          >
            Schema Details
          </button>
        </li>
      </ul>

      {activeTab === 'tables' && (
        <div className="tables-tab">
          <h3 className="mb-3">Tables</h3>
          {tables.length === 0 ? (
            <div className="alert alert-info">No tables found in this dataset</div>
          ) : (
            <div className="row">
              {tables.map(table => (
                <div className="col-md-6 mb-4" key={table.id}>
                  <div className="card h-100">
                    <div className="card-header">
                      <h5 className="mb-0">{table.name}</h5>
                    </div>
                    <div className="card-body">
                      <p><strong>Rows:</strong> {table.row_count}</p>
                      <p><strong>Columns:</strong> {table.column_count}</p>
                      
                      {table.columns && table.columns.length > 0 && (
                        <div>
                          <h6 className="mt-3">Columns</h6>
                          <ul className="list-group">
                            {table.columns.map(column => (
                              <li key={column.id} className="list-group-item d-flex justify-content-between align-items-center">
                                {column.name}
                                <span className="badge bg-primary rounded-pill">
                                  {column.data_type}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'schema' && (
        <div className="schema-tab">
          <h3 className="mb-3">Schema Details</h3>
          {!schema ? (
            <div className="alert alert-info">No schema information available</div>
          ) : (
            <div className="card">
              <div className="card-body">
                <pre className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(schema, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DatasetDetail;