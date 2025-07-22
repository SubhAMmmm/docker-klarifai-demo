import axios from 'axios';

const API_URL = 'https://klarifai-docker-demo-a8dahxe4fwa8bja9.canadacentral-01.azurewebsites.net/api';

// Create axios instance with base URL
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dataset services
export const datasetService = {
  // Get all datasets
  getAllDatasets: async () => {
    try {
      const response = await apiClient.get('/datasets/');
      return response.data;
    } catch (error) {
      console.error('Error fetching datasets:', error);
      throw error;
    }
  },

  // Get dataset by ID
  getDataset: async (datasetId) => {
    try {
      const response = await apiClient.get(`/datasets/${datasetId}/`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching dataset ${datasetId}:`, error);
      throw error;
    }
  },

  // Upload a new dataset
  uploadDataset: async (formData) => {
    try {
      // Use FormData for file uploads
      const response = await apiClient.post('/datasets/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading dataset:', error);
      throw error;
    }
  },

  // Get dataset schema
  getDatasetSchema: async (datasetId) => {
    try {
      const response = await apiClient.get(`/datasets/${datasetId}/schema/`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching schema for dataset ${datasetId}:`, error);
      throw error;
    }
  },

  // Get dataset tables
  getDatasetTables: async (datasetId) => {
    try {
      const response = await apiClient.get(`/datasets/${datasetId}/tables/`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching tables for dataset ${datasetId}:`, error);
      throw error;
    }
  },
};

// Query services
export const queryService = {
  // Create a new query
  createQuery: async (datasetId, question) => {
    try {
      const response = await apiClient.post('/queries/', {
        dataset: datasetId,
        question: question,
      });
      return response.data;
    } catch (error) {
      console.error('Error creating query:', error);
      throw error;
    }
  },

  // Get query results
  getQueryResults: async (queryId) => {
    try {
      const response = await apiClient.get(`/queries/${queryId}/results/`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching results for query ${queryId}:`, error);
      throw error;
    }
  },

  // Get query history
  getQueryHistory: async () => {
    try {
      const response = await apiClient.get('/queries/');
      return response.data;
    } catch (error) {
      console.error('Error fetching query history:', error);
      throw error;
    }
  },
};