import React, { useState } from 'react';
import FileUploader from '../components/FileUploader';
import DatasetList from '../components/DatasetList';

const Home = () => {
  const [newDataset, setNewDataset] = useState(null);

  const handleUploadSuccess = (dataset) => {
    setNewDataset(dataset);
  };

  return (
    <div className="home-page">
      <div className="row">
        <div className="col-lg-12 mb-4">
          <div className="jumbotron bg-light p-4 rounded">
            <h1 className="display-4">Data Analysis App</h1>
            <p className="lead">
              Upload CSV or Excel files, ask questions in natural language, and get insights from your data
            </p>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col-lg-4">
          <FileUploader onUploadSuccess={handleUploadSuccess} />
        </div>
        <div className="col-lg-8">
          <DatasetList newDataset={newDataset} />
        </div>
      </div>
    </div>
  );
};

export default Home;