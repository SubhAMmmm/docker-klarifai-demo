from rest_framework import serializers
from .models import Dataset, DataTable, TableColumn, Query

class TableColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableColumn
        fields = ['id', 'name', 'data_type', 'nullable']

class DataTableSerializer(serializers.ModelSerializer):
    columns = TableColumnSerializer(many=True, read_only=True)
    
    class Meta:
        model = DataTable
        fields = ['id', 'name', 'row_count', 'column_count', 'columns']

class DatasetSerializer(serializers.ModelSerializer):
    tables = DataTableSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dataset
        fields = ['id', 'name', 'file', 'file_type', 'created_at', 'tables']
        read_only_fields = ['id', 'created_at']
    
    def validate_file(self, value):
        # Get file extension to validate file type
        file_extension = value.name.split('.')[-1].lower()
        
        if file_extension not in ['csv', 'xlsx', 'xls']:
            raise serializers.ValidationError("Unsupported file type. Please upload CSV or Excel files.")
        
        # Set the file_type field based on the extension
        self.initial_data['file_type'] = 'xlsx' if file_extension in ['xlsx', 'xls'] else 'csv'
        
        return value

class QuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Query
        fields = ['id', 'dataset', 'question', 'sql_query', 'result_json', 
                 'created_at', 'execution_time_ms', 'success', 'error_message']
        read_only_fields = ['id', 'sql_query', 'result_json', 'created_at', 
                           'execution_time_ms', 'success', 'error_message']

class QueryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Query
        fields = ['dataset', 'question']