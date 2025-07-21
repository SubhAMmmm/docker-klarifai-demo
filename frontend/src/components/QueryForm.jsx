import React, { useState } from 'react';
import { queryService } from '../services/api';

const QueryForm = ({ datasetId, onQuerySuccess }) => {
  const [question, setQuestion] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }

    try {
      setIsQuerying(true);
      setError('');

      const result = await queryService.createQuery(datasetId, question);
      
      setIsQuerying(false);
      
      if (onQuerySuccess) {
        onQuerySuccess(result);
      }
    } catch (err) {
      setIsQuerying(false);
      
      // Get the error message from the API response or use a generic message
      let errorMessage = "Failed to process query. Please try again.";
      
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        if (err.response.data && err.response.data.error) {
          errorMessage = err.response.data.error;
        } else if (err.response.status === 500) {
          errorMessage = "Server error: The application encountered an internal error. This might be due to missing API keys or server configuration.";
        } else if (err.response.status === 404) {
          errorMessage = "Resource not found: The requested data could not be found.";
        }
      } else if (err.request) {
        // The request was made but no response was received
        errorMessage = "Network error: Could not connect to the server. Please check your internet connection.";
      } 
      
      setError(errorMessage);
      console.error('Query error:', err);
    }
  };

  const exampleQuestions = [
    "What are the top 5 products by sales?",
    "Show me the monthly revenue trend",
    "Compare sales by region",
    "What's the average order value?",
    "Show distribution of customers by age"
  ];

  const setExampleQuestion = (question) => {
    setQuestion(question);
    setError('');
  };

  return (
    <div className="query-form">
      <h3 className="mb-3">Ask a Question About Your Data</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <textarea
            className="form-control"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., What are the top 5 customers by total sales?"
            required
          />
        </div>

        {error && (
          <div className="alert alert-danger">
            <strong>Error:</strong> {error}
            <div className="mt-2">
              <small>
                If you're seeing an internal error, please make sure you've set up:
                <ul className="mb-0">
                  <li>The Google API key in your .env file</li>
                  <li>The PostgreSQL database connection</li>
                  <li>All required Python dependencies</li>
                </ul>
              </small>
            </div>
          </div>
        )}

        <button 
          type="submit" 
          className="btn btn-primary"
          disabled={isQuerying || !question.trim()}
        >
          {isQuerying ? 'Analyzing...' : 'Analyze Data'}
        </button>
      </form>

      <div className="mt-4">
        <h6>Example Questions:</h6>
        <div className="d-flex flex-wrap gap-2">
          {exampleQuestions.map((q, index) => (
            <button
              key={index}
              className="btn btn-sm btn-outline-secondary"
              onClick={() => setExampleQuestion(q)}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default QueryForm;