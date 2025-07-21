import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';

const Visualization = ({ data }) => {
  const [vizType, setVizType] = useState('');
  const [plotData, setPlotData] = useState(null);
  const [layout, setLayout] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!data) return;

    console.log('Visualization data received:', data);

    // Determine the first available visualization type
    const availableTypes = Object.keys(data).filter(key => key !== 'error');
    if (availableTypes.length === 0) {
      setError('No visualization data available');
      return;
    }

    // Set the default visualization type to the first available
    const defaultType = availableTypes[0];
    setVizType(defaultType);
    
    // Parse the visualization data
    parseVisualizationData(defaultType);
  }, [data]);

  const parseVisualizationData = (type) => {
    if (!data || !data[type]) {
      setError(`No data available for ${type} visualization`);
      return;
    }

    try {
      const vizData = data[type];
      
      // Handle the special case for table data
      if (type === 'table') {
        // Create a simple bar chart from the table data
        createChartFromTableData(vizData);
        return;
      }
      
      // Parse Plotly data
      if (vizData.data && Array.isArray(vizData.data)) {
        setPlotData(vizData.data);
        setLayout(vizData.layout || {});
        setError('');
      } else {
        // If data structure is different, create a chart from whatever data is available
        createChartFromData(type, vizData);
      }
    } catch (err) {
      console.error('Error parsing visualization data:', err);
      setError(`Failed to parse visualization data: ${err.message}`);
      
      // Attempt to create a fallback visualization
      createFallbackVisualization();
    }
  };

  // Create a chart from table data (which is just an array of objects)
  const createChartFromTableData = (tableData) => {
    try {
      if (!Array.isArray(tableData) || tableData.length === 0) {
        throw new Error('Table data is empty or not in array format');
      }

      // Get the first object to determine its structure
      const firstItem = tableData[0];
      
      // Extract keys and values for the chart
      const keys = Object.keys(firstItem);
      const values = Object.values(firstItem);
      
      // Simple checks to determine the best chart type
      let chartType = 'bar';  // Default
      
      // If there's only one value, use a simple bar or number display
      if (keys.length === 1) {
        const data = [{
          type: 'bar',
          x: ['Result'],
          y: [values[0]],
          marker: {
            color: 'rgb(26, 118, 255)'
          }
        }];
        
        setPlotData(data);
        setLayout({
          title: `${keys[0]}`,
          autosize: true,
          margin: { l: 50, r: 50, b: 50, t: 80, pad: 4 }
        });
        setError('');
        return;
      }
      
      // If there are multiple items, create a more complex chart
      if (tableData.length > 1) {
        // Extract all values for each key
        const chartData = {};
        keys.forEach(key => {
          chartData[key] = tableData.map(item => item[key] || 0);
        });
        
        // Create arrays for x and y
        const xKey = keys[0];
        const yKey = keys[1] || keys[0];
        
        const data = [{
          type: 'bar',
          x: chartData[xKey] || Object.keys(chartData),
          y: chartData[yKey] || Object.values(chartData),
          marker: {
            color: 'rgb(26, 118, 255)'
          }
        }];
        
        setPlotData(data);
        setLayout({
          title: `${yKey} by ${xKey}`,
          autosize: true,
          margin: { l: 50, r: 50, b: 80, t: 80, pad: 4 }
        });
        setError('');
        return;
      }
      
      // Fallback for single value display
      const data = [{
        type: 'bar',
        x: keys,
        y: values,
        marker: {
          color: 'rgb(26, 118, 255)'
        }
      }];
      
      setPlotData(data);
      setLayout({
        title: 'Data Visualization',
        autosize: true,
        margin: { l: 50, r: 50, b: 80, t: 80, pad: 4 }
      });
      setError('');
      
    } catch (err) {
      console.error('Error creating chart from table data:', err);
      createFallbackVisualization();
    }
  };

  // Create a chart from any data structure
  const createChartFromData = (type, vizData) => {
    try {
      let chartData = [];
      
      if (Array.isArray(vizData)) {
        // If it's an array, try to extract data points
        if (vizData.length > 0) {
          // Check if array items are objects
          if (typeof vizData[0] === 'object') {
            const keys = Object.keys(vizData[0]);
            if (keys.length >= 2) {
              // Use first key as x and second as y
              chartData = [{
                type: 'bar',
                x: vizData.map(item => item[keys[0]]),
                y: vizData.map(item => item[keys[1]]),
                marker: { color: 'rgb(26, 118, 255)' }
              }];
            } else {
              // Simple case with one value per object
              chartData = [{
                type: 'bar',
                x: vizData.map((_, index) => `Item ${index + 1}`),
                y: vizData.map(item => Object.values(item)[0]),
                marker: { color: 'rgb(26, 118, 255)' }
              }];
            }
          } else {
            // Simple array of values
            chartData = [{
              type: 'bar',
              x: vizData.map((_, index) => `Item ${index + 1}`),
              y: vizData,
              marker: { color: 'rgb(26, 118, 255)' }
            }];
          }
        }
      } else if (typeof vizData === 'object') {
        // Object with properties
        chartData = [{
          type: 'bar',
          x: Object.keys(vizData),
          y: Object.values(vizData),
          marker: { color: 'rgb(26, 118, 255)' }
        }];
      }
      
      if (chartData.length > 0) {
        setPlotData(chartData);
        setLayout({
          title: `${type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}`,
          autosize: true,
          margin: { l: 50, r: 50, b: 80, t: 80, pad: 4 }
        });
        setError('');
      } else {
        throw new Error('Could not create chart from data');
      }
    } catch (err) {
      console.error('Error creating chart from data:', err);
      createFallbackVisualization();
    }
  };

  // Create a fallback visualization when all else fails
  const createFallbackVisualization = () => {
    const fallbackData = [{
      type: 'bar',
      x: ['Result'],
      y: [100],
      text: ['Result value'],
      marker: {
        color: 'rgb(26, 118, 255)'
      }
    }];
    
    setPlotData(fallbackData);
    setLayout({
      title: 'Data Visualization',
      autosize: true,
      margin: { l: 50, r: 50, b: 50, t: 80, pad: 4 },
      annotations: [{
        x: 0.5,
        y: 0.5,
        xref: 'paper',
        yref: 'paper',
        text: 'Visualization could not be generated with the provided data',
        showarrow: false,
        font: {
          size: 14
        }
      }]
    });
    setError('');
  };

  const handleTypeChange = (type) => {
    setVizType(type);
    parseVisualizationData(type);
  };

  // If visualization data is unavailable
  if (!data || Object.keys(data).length === 0) {
    return <div className="alert alert-info">No visualization data available</div>;
  }

  // If there's an error in the data
  if (data.error) {
    return <div className="alert alert-warning">{data.error}</div>;
  }

  // If there's an error in parsing
  if (error) {
    return (
      <div>
        <div className="viz-type-selector mb-3">
          {Object.keys(data).filter(key => key !== 'error').map(type => (
            <button
              key={type}
              className={`btn btn-sm ${vizType === type ? 'btn-primary' : 'btn-outline-primary'} me-2`}
              onClick={() => handleTypeChange(type)}
            >
              {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
            </button>
          ))}
        </div>
        <div className="alert alert-warning">
          {error}
          <div className="mt-2">
            <small>Try selecting a different visualization type if available, or check the data table below.</small>
          </div>
        </div>
      </div>
    );
  }

  // If plotData is not available
  if (!plotData) {
    return (
      <div>
        <div className="viz-type-selector mb-3">
          {Object.keys(data).filter(key => key !== 'error').map(type => (
            <button
              key={type}
              className={`btn btn-sm ${vizType === type ? 'btn-primary' : 'btn-outline-primary'} me-2`}
              onClick={() => handleTypeChange(type)}
            >
              {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
            </button>
          ))}
        </div>
        <div className="alert alert-info">Preparing visualization...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="viz-type-selector mb-3">
        {Object.keys(data).filter(key => key !== 'error').map(type => (
          <button
            key={type}
            className={`btn btn-sm ${vizType === type ? 'btn-primary' : 'btn-outline-primary'} me-2`}
            onClick={() => handleTypeChange(type)}
          >
            {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
          </button>
        ))}
      </div>
      
      <div className="plot-container" style={{ height: '400px', width: '100%', backgroundColor: '#fff', padding: '15px', borderRadius: '8px' }}>
        <Plot
          data={plotData}
          layout={{
            ...layout,
            autosize: true,
            responsive: true,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {
              family: 'Arial, sans-serif'
            }
          }}
          useResizeHandler={true}
          style={{ width: '100%', height: '100%' }}
          config={{ 
            displayModeBar: true, 
            responsive: true,
            displaylogo: false,
            modeBarButtonsToRemove: [
              'lasso2d', 
              'select2d'
            ]
          }}
        />
      </div>
    </div>
  );
};

export default Visualization;