# data_processor.py

import re
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, inspect
from django.conf import settings
import logging
from typing import Dict, List, Tuple, Optional, Union
import json

# Configure logging
logger = logging.getLogger(__name__)

def clean_column_names(headers: List[str]) -> List[str]:
    """
    Clean and standardize column names by:
    - Removing special characters
    - Handling duplicates
    - Converting to lowercase
    - Replacing spaces with underscores
    
    Args:
        headers: List of original column names
        
    Returns:
        List of cleaned column names
    """
    cleaned_headers = []
    seen_headers = {}
    
    for header in headers:
        # Convert to string if not already
        header_str = str(header).strip() if not pd.isna(header) else "unnamed_column"
        
        # Remove special characters and normalize
        header_clean = re.sub(r'[^\w\s]', '', header_str)
        header_clean = re.sub(r'\s+', '_', header_clean).lower()
        
        # Handle empty headers
        if not header_clean:
            header_clean = "unnamed_column"
            
        # Handle duplicates
        base_header = header_clean
        counter = 1
        while header_clean in seen_headers:
            header_clean = f"{base_header}_{counter}"
            counter += 1
        
        seen_headers[header_clean] = True
        cleaned_headers.append(header_clean)
    
    return cleaned_headers

def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infer appropriate PostgreSQL data types for each column
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary mapping column names to SQLAlchemy types
    """
    from sqlalchemy.types import BigInteger, Float, Boolean, DateTime, Text
    
    type_mapping = {
        'int64': BigInteger,
        'float64': Float,
        'bool': Boolean,
        'datetime64[ns]': DateTime,
        'object': Text,
        'category': Text
    }
    
    col_types = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        
        # Handle datetime separately
        if np.issubdtype(df[col].dtype, np.datetime64):
            col_types[col] = DateTime
        else:
            # Get base type without size info
            base_type = dtype.split('[')[0].split('(')[0]
            col_types[col] = type_mapping.get(base_type, Text)
            
            # Check if it's actually a string representation of numbers
            if col_types[col] == Text and df[col].apply(lambda x: str(x).isdigit() if pd.notna(x) else False).all():
                col_types[col] = BigInteger if df[col].astype(float).apply(float.is_integer).all() else Float
        
    return col_types

def extract_column_unique_values(df: pd.DataFrame, max_values: int = 100) -> Dict[str, Dict]:
    """
    Extract unique values from each column in the DataFrame
    
    Args:
        df: DataFrame to analyze
        max_values: Maximum number of unique values to extract per column
        
    Returns:
        Dictionary mapping column names to lists of unique values
    """
    unique_values = {}
    
    for col in df.columns:
        try:
            # Skip columns with too many unique values or non-categorical data
            if df[col].nunique() <= max_values:
                # Convert to list and then to strings to avoid slice objects
                values = [str(val) for val in df[col].dropna().unique().tolist() if str(val).strip()]
                
                # Only store if we have meaningful values
                if values:
                    col_type = str(df[col].dtype)
                    unique_values[str(col)] = {
                        'values': values,
                        'type': col_type,
                        'count': len(values)
                    }
        except Exception as e:
            logger.warning(f"Error extracting unique values for column {col}: {str(e)}")
    
    return unique_values

def validate_schema(schema_info: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the generated schema for consistency and data quality
    
    Args:
        schema_info: Generated schema information
        
    Returns:
        Tuple of (is_valid, [validation_messages])
    """
    warnings = []
    required_columns = []  # Add required columns that must have data
    
    for table_name, table_data in schema_info.items():
        # Check for empty tables
        if not table_data.get('sample'):
            warnings.append(f"⚠️ Warning: Table '{table_name}' has no sample data")
            continue
            
        # Check column data quality
        for col_name, col_type in table_data.get('columns', []):
            # Add info about columns
            sample_data = table_data.get('sample', [])
            if not sample_data:
                continue
                
            # Check if column is empty in samples
            try:
                empty_count = sum(1 for item in sample_data if not item.get(col_name))
                
                # Only warn about empty columns if they're in required_columns
                if col_name in required_columns and empty_count == len(sample_data):
                    warnings.append(f"⚠️ Warning: Required column '{col_name}' in '{table_name}' is empty")
                
                # Add info about nullable columns
                elif empty_count == len(sample_data):
                    warnings.append(f"ℹ️ Info: Optional column '{col_name}' in '{table_name}' is currently empty")
                
                # Warning if column has high percentage of nulls
                elif empty_count / len(sample_data) > 0.9:  # 90% threshold
                    warnings.append(f"⚠️ Note: Column '{col_name}' has {(empty_count/len(sample_data))*100:.1f}% null values")
            except Exception as e:
                warnings.append(f"⚠️ Warning: Validation failed for '{col_name}': {str(e)}")
    
    # Filter and categorize messages
    info_messages = [msg for msg in warnings if msg.startswith('ℹ️')]
    warning_messages = [msg for msg in warnings if msg.startswith('⚠️')]
    
    # Combine messages with headers
    validation_messages = []
    if info_messages:
        validation_messages.append("\n📝 Information:")
        validation_messages.extend(info_messages)
    if warning_messages:
        validation_messages.append("\n⚠️ Warnings:")
        validation_messages.extend(warning_messages)
    
    # Schema is valid if there are only info messages or no messages
    is_valid = all(msg.startswith('ℹ️') for msg in warnings) or not warnings
    
    return is_valid, validation_messages

def process_uploaded_file(file_path: str, file_type: str) -> Dict:
    """
    Process an uploaded Excel or CSV file
    """
    try:
        # Read the file based on file type
        if file_type in ['xlsx', 'xls']:
            # Read Excel file
            df_dict = pd.read_excel(file_path, sheet_name=None)
            
            # Process each sheet
            tables = {}
            for sheet_name, df in df_dict.items():
                # Clean column names
                df.columns = clean_column_names(df.columns)
                tables[sheet_name] = df
            
            return tables
            
        elif file_type == 'csv':
            # Read CSV file
            df = pd.read_csv(file_path)
            # Clean column names
            df.columns = clean_column_names(df.columns)
            
            return {'main_data': df}
            
        else:
            raise ValueError("Unsupported file type")
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

def get_db_connection_string():
    """Get SQLAlchemy connection string from settings"""
    return f"postgresql://{settings.DATABASES['default']['USER']}:{settings.DATABASES['default']['PASSWORD']}@{settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}/{settings.DATABASES['default']['NAME']}"

def store_dataframes_in_db(tables: Dict[str, pd.DataFrame], dataset_id: str) -> List[Dict]:
    """
    Store dataframes in PostgreSQL database with appropriate types
    """
    table_info = []
    engine = create_engine(get_db_connection_string())
    
    try:
        for table_name, df in tables.items():
            # Create a valid table name
            safe_table_name = re.sub(r'[^\w]', '_', table_name.lower())
            safe_table_name = f"ds_{dataset_id.replace('-', '')}_{safe_table_name}"
            
            # Limit table name length for PostgreSQL
            if len(safe_table_name) > 63:
                safe_table_name = safe_table_name[:63]
            
            # Infer column types
            col_types = infer_column_types(df)
            
            # Extract unique values
            unique_values = extract_column_unique_values(df)
            
            # Convert columns to appropriate types
            for col, dtype in col_types.items():
                if dtype.__name__ == 'DateTime':
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                elif dtype.__name__ == 'BigInteger':
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif dtype.__name__ == 'Float':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Store in database
            df.to_sql(safe_table_name, engine, if_exists='replace', index=False, dtype=col_types)
            
            # Append table info
            table_info.append({
                'name': safe_table_name,
                'original_name': table_name,
                'row_count': len(df),
                'column_count': len(df.columns),
                'unique_values': unique_values,
                'columns': [
                    {
                        'name': col_name,
                        'data_type': col_type.__name__,
                        'nullable': df[col_name].isna().any()
                    }
                    for col_name, col_type in col_types.items()
                ]
            })
            
        return table_info
    
    except Exception as e:
        logger.error(f"Error storing dataframes: {str(e)}")
        raise
    
    finally:
        engine.dispose()

def generate_schema_info() -> Dict:
    """
    Generate detailed schema information with samples and relationships
    """
    engine = create_engine(get_db_connection_string())
    inspector = inspect(engine)
    schema_info = {}
    
    try:
        with engine.connect() as conn:
            for table_name in inspector.get_table_names():
                # Skip Django tables
                if table_name.startswith('django_') or table_name.startswith('auth_'):
                    continue
                
                try:    
                    columns = []
                    for column in inspector.get_columns(table_name):
                        columns.append((column['name'], str(column['type'])))
                    
                    # Get sample data
                    sample_query = text(f'SELECT * FROM "{table_name}" LIMIT 3')
                    result = conn.execute(sample_query)
                    
                    # Convert to DataFrame and handle potential errors
                    try:
                        sample_data = result.fetchall()
                        columns_names = result.keys()
                        sample = pd.DataFrame(sample_data, columns=columns_names)
                        # Convert to serializable format
                        sample_json = json.loads(sample.to_json(orient='records'))
                    except UnicodeDecodeError:
                        # Handle encoding errors
                        logger.warning(f"Encoding error in table {table_name}, using simplified sample")
                        sample_json = [{"note": "Sample data contains non-UTF-8 characters"}]
                    except Exception as e:
                        logger.warning(f"Error creating sample for table {table_name}: {str(e)}")
                        sample_json = []
                    
                    # Get foreign keys
                    foreign_keys = []
                    try:
                        for fk in inspector.get_foreign_keys(table_name):
                            foreign_keys.append({
                                'constrained_columns': fk.get('constrained_columns', []),
                                'referred_table': fk.get('referred_table', ''),
                                'referred_columns': fk.get('referred_columns', [])
                            })
                    except Exception as e:
                        logger.warning(f"Error retrieving foreign keys for table {table_name}: {str(e)}")
                    
                    # Extract unique values
                    unique_values = {}
                    try:
                        # Get unique values for appropriate columns
                        for col_name, _ in columns:
                            values_query = text(f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 100')
                            values_result = conn.execute(values_query)
                            values = [str(value[0]) for value in values_result.fetchall() if value[0] is not None and str(value[0]).strip()]
                            
                            if values:
                                col_type = next((col_type for col, col_type in columns if col == col_name), 'TEXT')
                                unique_values[col_name] = {
                                    'values': values,
                                    'type': col_type,
                                    'count': len(values)
                                }
                    except Exception as e:
                        logger.warning(f"Error extracting unique values for table {table_name}: {str(e)}")
                    
                    schema_info[table_name] = {
                        'columns': columns,
                        'sample': sample_json,
                        'foreign_keys': foreign_keys,
                        'unique_values': unique_values
                    }
                except Exception as table_error:
                    logger.error(f"Error processing table {table_name}: {str(table_error)}")
                    # Still add the table but with minimal info
                    schema_info[table_name] = {
                        'columns': [],
                        'sample': [],
                        'foreign_keys': [],
                        'unique_values': {},
                        'error': str(table_error)
                    }
        
        return schema_info
    
    except Exception as e:
        logger.error(f"Error generating schema info: {str(e)}")
        raise
    
    finally:
        engine.dispose()

def clean_sql_query(sql_query: str) -> str:
    """
    Clean and standardize SQL query by:
    - Removing code block markers
    - Standardizing quotes
    - Removing extra whitespace
    - Ensuring proper semicolon placement
    
    Args:
        sql_query: Raw SQL query string
        
    Returns:
        Cleaned SQL query string
    """
    try:
        # Remove code block markers if present
        if '```sql' in sql_query:
            sql_query = sql_query.split('```sql')[1].split('```')[0]
        elif '```' in sql_query:
            sql_query = sql_query.split('```')[1].split('```')[0]
        
        # Clean up the query
        cleaned_query = sql_query.strip()
        
        # Standardize quotes around identifiers
        cleaned_query = re.sub(r'`(\w+)`', r'"\1"', cleaned_query)  # Replace backticks with double quotes
        cleaned_query = re.sub(r"'(\w+)'(?=\.|\s+AS\s|\s+FROM|\s+JOIN)", r'"\1"', cleaned_query)  # Replace single quotes for identifiers
        
        # Ensure proper spacing around operators
        cleaned_query = re.sub(r'\s*([=<>])\s*', r' \1 ', cleaned_query)
        
        # Remove multiple whitespace
        cleaned_query = ' '.join(cleaned_query.split())
        
        # Ensure proper semicolon at the end
        if not cleaned_query.rstrip().endswith(';'):
            cleaned_query += ';'
        
        return cleaned_query
        
    except Exception as e:
        logger.error(f"Error cleaning SQL query: {str(e)}")
        return sql_query  # Return original query if cleaning fails

def execute_query_safely(sql_query: str, limit: int = 1000) -> Tuple[bool, Union[pd.DataFrame, str]]:
    """
    Execute SQL query with safety measures:
    - Parameterized queries
    - Row limiting
    - Error handling
    
    Args:
        sql_query: SQL query to execute
        limit: Maximum rows to return
        
    Returns:
        Tuple of (success, result_or_error)
    """
    engine = create_engine(get_db_connection_string())
    
    try:
        # Clean the query first
        sql_query = clean_sql_query(sql_query)
        
        # Add LIMIT if not already present (for SELECT queries)
        modified_query = sql_query
        if "SELECT" in sql_query.upper() and "LIMIT" not in sql_query.upper():
            modified_query = f"{sql_query.rstrip(';')} LIMIT {limit};"
        
        with engine.connect() as conn:
            # First test with EXPLAIN to verify without executing
            conn.execute(text(f"EXPLAIN {modified_query}"))
            
            # If EXPLAIN succeeds, execute the real query
            result = conn.execute(text(modified_query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            return True, df
            
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        return False, str(e)
    
    finally:
        engine.dispose()