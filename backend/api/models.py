from django.db import models
import uuid

class Dataset(models.Model):
    """Model for uploaded datasets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='datasets/')
    file_type = models.CharField(max_length=10, choices=[
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
        ('xls', 'Excel (old)')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class DataTable(models.Model):
    """Model for database tables created from datasets"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='tables')
    name = models.CharField(max_length=255)
    row_count = models.IntegerField()
    column_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class TableColumn(models.Model):
    """Model for columns in data tables"""
    table = models.ForeignKey(DataTable, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=50)
    nullable = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.table.name}.{self.name}"

class Query(models.Model):
    """Model for storing user queries and results"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='queries')
    question = models.TextField()
    sql_query = models.TextField()
    result_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    execution_time_ms = models.IntegerField(null=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Queries"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.question