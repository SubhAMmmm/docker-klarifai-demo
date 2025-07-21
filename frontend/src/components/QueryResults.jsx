import React from 'react';
import Visualization from './Visualization';
import ReactMarkdown from 'react-markdown';

const QueryResults = ({ results }) => {
  if (!results) {
    return null;
  }

  if (results.error) {
    return <div className="alert alert-danger">{results.error}</div>;
  }

  const { sql_query, result } = results;
  
  if (!result || !result.data || result.data.length === 0) {
    return (
      <div className="alert alert-info">
        No data found for this query. Try a different question.
      </div>
    );
  }

  return (
    <div className="query-results mt-4">
      <h3 className="mb-3">Analysis Results</h3>
      
      {sql_query && (
        <div className="card mb-4">
          <div className="card-header">
            <h5 className="mb-0">Generated SQL Query</h5>
          </div>
          <div className="card-body">
            <pre className="mb-0"><code>{sql_query}</code></pre>
          </div>
        </div>
      )}

      {result.analysis && (
        <div className="analysis-container mb-4">
          <h5 className="mb-3">Analysis</h5>
          <div className="markdown-content">
            <ReactMarkdown>
              {result.analysis}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {result.visualizations && Object.keys(result.visualizations).length > 0 && (
        <div className="visualization-container mb-4">
          <h5 className="mb-3">Visualization</h5>
          <Visualization data={result.visualizations} />
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Data Table</h5>
          <small className="text-muted">Showing {result.data.length} of {result.row_count} rows</small>
        </div>
        <div className="card-body p-0">
          <div className="results-table">
            <table className="table table-striped table-hover mb-0">
              <thead>
                <tr>
                  {result.columns.map((column, index) => (
                    <th key={index}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.data.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {result.columns.map((column, colIndex) => (
                      <td key={colIndex}>{row[column] !== null ? row[column] : 'NULL'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QueryResults;