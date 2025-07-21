import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import DatasetDetail from './pages/DatasetDetail'
import QueryPage from './pages/QueryPage'

function App() {
  return (
    <div className="App">
      <nav className="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div className="container">
          <Link className="navbar-brand" to="/">Data Analysis App</Link>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav">
              <li className="nav-item">
                <Link className="nav-link" to="/">Home</Link>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/datasets/:id" element={<DatasetDetail />} />
          <Route path="/datasets/:id/query" element={<QueryPage />} />
        </Routes>
      </div>

      <footer className="mt-5 py-3 text-center text-muted">
        <div className="container">
          <p>Data Analysis Application &copy; {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  )
}

export default App