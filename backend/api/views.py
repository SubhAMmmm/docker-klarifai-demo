import os
import tempfile
import time
import json
from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Dataset, DataTable, TableColumn, Query
from .serializers import (
    DatasetSerializer, DataTableSerializer, 
    QuerySerializer, QueryCreateSerializer
)

from .services.data_processor import (
    process_uploaded_file, store_dataframes_in_db, 
    generate_schema_info, execute_query_safely,
    clean_sql_query, validate_schema
)
from .services.query_generator import (
    generate_sql_query, validate_query, 
    refine_query, format_value_matches
)
from .services.analyzer import generate_analysis_explanation, visualize_results
import pandas as pd
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DatasetViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing datasets
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [AllowAny]  # Use IsAuthenticated in production
    
    def create(self, request, *args, **kwargs):
        """Upload and process a new dataset"""
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                # Save dataset record
                try:
                    dataset = serializer.save()
                    
                    # Process the uploaded file
                    file_path = dataset.file.path
                    file_type = dataset.file_type
                    
                    # Process file
                    tables = process_uploaded_file(file_path, file_type)
                    
                    # Store in database
                    table_info = store_dataframes_in_db(tables, str(dataset.id))
                    
                    # Create table records
                    for table in table_info:
                        data_table = DataTable.objects.create(
                            dataset=dataset,
                            name=table['name'],
                            row_count=table['row_count'],
                            column_count=table['column_count']
                        )
                        
                        # Create column records
                        for col in table['columns']:
                            TableColumn.objects.create(
                                table=data_table,
                                name=col['name'],
                                data_type=col['data_type'],
                                nullable=col['nullable']
                            )
                        
                        # Store unique values metadata
                        if 'unique_values' in table:
                            data_table.metadata = {'unique_values': table['unique_values']}
                            data_table.save()
                    
                    # Return serialized dataset with tables
                    return Response(
                        self.get_serializer(dataset).data,
                        status=status.HTTP_201_CREATED
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    # Clean up on error
                    if 'dataset' in locals():
                        dataset.delete()
                    return Response(
                        {'error': f"Error processing file: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as outer_e:
            logger.error(f"Outer exception in dataset creation: {str(outer_e)}")
            return Response(
                {'error': f"Server error: {str(outer_e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def tables(self, request, pk=None):
        """Get tables for a dataset"""
        try:
            dataset = self.get_object()
            tables = DataTable.objects.filter(dataset=dataset)
            serializer = DataTableSerializer(tables, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def schema(self, request, pk=None):
        """Get database schema for a dataset"""
        try:
            dataset = self.get_object()
            # Get the tables created for this dataset
            tables = DataTable.objects.filter(dataset=dataset).values_list('name', flat=True)
            
            if not tables:
                return Response(
                    {"error": "No tables found for this dataset"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Get schema info for these tables
            schema_info = generate_schema_info()
            
            # Filter schema to only include tables for this dataset
            # Handle the case where tables might not exist in the schema
            filtered_schema = {}
            for table_name in tables:
                if table_name in schema_info:
                    filtered_schema[table_name] = schema_info[table_name]
            
            # If no tables were found in schema
            if not filtered_schema:
                return Response(
                    {"message": "Tables exist but schema info could not be retrieved"},
                    status=status.HTTP_200_OK
                )
                
            # Validate schema for data quality issues
            is_valid, validation_messages = validate_schema(filtered_schema)
            if not is_valid:
                logger.warning("Schema validation issues found")
                for msg in validation_messages:
                    logger.warning(msg)
                
            return Response({
                'schema': filtered_schema,
                'validation': {
                    'is_valid': is_valid,
                    'messages': validation_messages if not is_valid else []
                }
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class QueryViewSet(viewsets.ModelViewSet):
    """
    API endpoints for handling natural language queries
    """
    queryset = Query.objects.all()
    permission_classes = [AllowAny]  # Use IsAuthenticated in production
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QueryCreateSerializer
        return QuerySerializer
    
    def create(self, request, *args, **kwargs):
        """Run a natural language query against a dataset"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Get validated data
            dataset_id = serializer.validated_data['dataset'].id
            question = serializer.validated_data['question']
            
            try:
                # Create query record
                query = Query.objects.create(
                    dataset_id=dataset_id,
                    question=question,
                    sql_query="",
                    success=False
                )
                
                # Get dataset tables
                dataset = Dataset.objects.get(id=dataset_id)
                tables = DataTable.objects.filter(dataset=dataset).values_list('name', flat=True)
                
                # Get schema information
                schema_info = generate_schema_info()
                filtered_schema = {k: v for k, v in schema_info.items() if k in tables}
                
                start_time = time.time()
                
                # Generate SQL query
                try:
                    sql_query = generate_sql_query(question, filtered_schema)
                except Exception as gen_error:
                    logger.error(f"Error generating SQL query: {str(gen_error)}")
                    query.error_message = f"Failed to generate SQL: {str(gen_error)}"
                    query.save()
                    return Response(
                        {'error': str(gen_error), 'query_id': query.id},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Clean the query
                sql_query = clean_sql_query(sql_query)
                
                # Validate query
                is_valid, validation_msg = validate_query(sql_query, filtered_schema)
                if not is_valid:
                    query.error_message = validation_msg
                    query.save()
                    return Response(
                        {'error': validation_msg, 'query_id': query.id},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Execute query
                success, result = execute_query_safely(sql_query)
                
                # If query failed, try to refine it
                if not success and hasattr(result, 'lower') and ('error' in result.lower() or 'exception' in result.lower()):
                    logger.info("Initial query failed, attempting refinement")
                    
                    # Initialize LLM for refinement
                    from .services.query_generator import initialize_llm, generate_schema_string
                    llm = initialize_llm()
                    schema_str = generate_schema_string(filtered_schema)
                    
                    # Try to refine the query
                    refined_query = refine_query(sql_query, result, schema_str, llm)
                    
                    if refined_query != sql_query:
                        logger.info("Query refined, retrying execution")
                        # Execute the refined query
                        success, result = execute_query_safely(refined_query)
                        if success:
                            sql_query = refined_query  # Use the refined version
                
                # Calculate execution time
                execution_time = int((time.time() - start_time) * 1000)  # in milliseconds
                
                if success:
                    if isinstance(result, pd.DataFrame):
                        # Generate analysis
                        analysis = generate_analysis_explanation(result, question)
                        
                        # Generate visualizations
                        viz_data = visualize_results(result, question)
                        
                        # Prepare result JSON
                        result_json = {
                            'data': result.to_dict(orient='records'),
                            'columns': list(result.columns),
                            'row_count': len(result),
                            'analysis': analysis,
                            'visualizations': viz_data
                        }
                        
                        # Update query record
                        query.sql_query = sql_query
                        query.result_json = result_json
                        query.execution_time_ms = execution_time
                        query.success = True
                        query.save()
                        
                        # Return response
                        return Response({
                            'query_id': query.id,
                            'sql_query': sql_query,
                            'result': result_json,
                            'execution_time_ms': execution_time
                        })
                    else:
                        raise ValueError("Query result is not a DataFrame")
                else:
                    query.sql_query = sql_query
                    query.error_message = str(result)
                    query.execution_time_ms = execution_time
                    query.save()
                    
                    return Response(
                        {'error': str(result), 'query_id': query.id, 'sql_query': sql_query},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            except Exception as e:
                if 'query' in locals():
                    query.error_message = str(e)
                    query.save()
                
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get results for a specific query"""
        try:
            query = self.get_object()
            return Response({
                'question': query.question,
                'sql_query': query.sql_query,
                'result': query.result_json,
                'success': query.success,
                'execution_time_ms': query.execution_time_ms,
                'error_message': query.error_message,
                'created_at': query.created_at
            })
        except Query.DoesNotExist:
            raise Http404