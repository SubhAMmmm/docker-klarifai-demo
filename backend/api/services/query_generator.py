# query_generator.py

import json
import re
from typing import Dict, List, Tuple
import logging
from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Configure logging
logger = logging.getLogger(__name__)

def get_prompt_template() -> PromptTemplate:
    """
    Create a prompt template for SQL generation
    """
    template = """
# SQL Data Analysis Prompt

## QUESTION METADATA:
{metadata}

## DATABASE SCHEMA:
{schema}

## MOST RELEVANT TABLES:
{relevant_tables}

## COLUMN VALUE MATCHES:
{value_matches}

## USER QUESTION:
{question}

## GENERATION RULES:
1. Use the provided metadata to guide query construction
2. Return ONLY the SQL query without explanations
3. Use appropriate aggregations based on the intent
4. Include filters from metadata
5. Apply sorting and limits as specified
6. Handle NULL values with COALESCE
7. Use proper JOIN conditions
8. Include WHERE clauses based on filters and exact value matches
9. Use GROUP BY when needed
10. Apply proper date/time handling
11. Use LIKE with wildcards for partial matches when appropriate
12. When filtering with column values:
   - For exact matches detected in the question, use exact equality (=)
   - For high confidence partial matches, use LIKE or similar pattern matching
   - For low confidence partial matches, do not include them unless absolutely necessary
13. Be precise with string comparisons - only use the exact values mentioned in the question or column_filters

Generate only the PostgreSQL-compatible SQL query:
"""
    return PromptTemplate(
        input_variables=["question", "schema", "relevant_tables", "metadata", "value_matches"],
        template=template
    )

def initialize_llm():
    """Initialize the language model for query generation"""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.0,
            google_api_key=settings.GOOGLE_API_KEY,
            convert_system_message_to_human=True
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {str(e)}")
        raise

def extract_relevant_tables(question: str, schema_info: Dict) -> str:
    """Identify likely relevant tables based on question keywords"""
    question_keywords = set(re.findall(r'\w+', question.lower()))
    relevant_tables = []
    
    for table_name, table_data in schema_info.items():
        table_score = 0
        columns = table_data['columns']
        
        # Score based on table name match
        table_words = set(re.findall(r'\w+', table_name.lower()))
        table_score += len(question_keywords.intersection(table_words)) * 3
        
        # Score based on column matches
        for col_name, col_type in columns:
            col_words = set(re.findall(r'\w+', col_name.lower()))
            table_score += len(question_keywords.intersection(col_words))
        
        if table_score > 0:
            relevant_tables.append((table_name, table_score))
    
    # Sort by relevance score
    relevant_tables.sort(key=lambda x: x[1], reverse=True)
    
    # Return top 2 tables with examples
    if not relevant_tables:
        return "No specific tables identified - check all tables."
    
    top_tables = [t[0] for t in relevant_tables[:2]]
    examples = []
    
    for table in top_tables:
        cols = [col[0] for col in schema_info[table]['columns'][:3]]
        examples.append(f"- {table} (columns: {', '.join(cols)})")
    
    return "\n".join(examples)

def match_question_with_column_values(question: str, schema_info: Dict) -> Dict[str, Dict]:
    """
    Match words in the user's question with column values from the database,
    supporting both exact and partial matches
    
    Args:
        question: User's question
        schema_info: Database schema information
        
    Returns:
        Dictionary mapping column names to matched values with confidence levels
    """
    matches = {}
    question_terms = re.findall(r'\b\w+\b', question.lower())
    question_phrases = []
    
    # Extract quoted phrases
    quoted_phrases = re.findall(r'[\'"]([^\'"]+)[\'"]', question)
    if quoted_phrases:
        question_phrases.extend([phrase.lower() for phrase in quoted_phrases])
    
    # Extract possible multi-word terms (up to 3 words)
    words = question.lower().split()
    for i in range(len(words)):
        if i+1 < len(words):
            question_phrases.append(f"{words[i]} {words[i+1]}")
        if i+2 < len(words):
            question_phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    # For each table and column with unique values
    for table_name, table_data in schema_info.items():
        if 'unique_values' not in table_data:
            continue
            
        unique_values = table_data['unique_values']
        for col_name, col_data in unique_values.items():
            exact_matches = []
            partial_matches = []
            quoted_matches = []
            
            if not isinstance(col_data, dict) or 'values' not in col_data:
                continue
                
            for db_value in col_data['values']:
                db_value_lower = str(db_value).lower()
                
                # Check for exact matches
                if db_value_lower in question_terms:
                    exact_matches.append({
                        'value': db_value,
                        'confidence': 'high',
                        'match_type': 'exact'
                    })
                    continue
                    
                # Check for quoted phrases
                if db_value_lower in question_phrases:
                    quoted_matches.append({
                        'value': db_value,
                        'confidence': 'high',
                        'match_type': 'phrase'
                    })
                    continue
                
                # Check for partial matches (when the DB value contains multiple words)
                if len(db_value_lower.split()) > 1:
                    if any(term in db_value_lower for term in question_terms):
                        partial_matches.append({
                            'value': db_value,
                            'confidence': 'medium',
                            'match_type': 'partial'
                        })
                        continue
                
                # Check if question terms are part of this value
                for term in question_terms:
                    if len(term) >= 3 and term in db_value_lower:
                        # Check if it's at the beginning of the value or a complete word
                        if db_value_lower.startswith(term) or f" {term} " in f" {db_value_lower} ":
                            partial_matches.append({
                                'value': db_value,
                                'confidence': 'low',
                                'match_type': 'contained'
                            })
                            break
            
            # Combine results with priority
            all_matches = exact_matches + quoted_matches + partial_matches
            
            if all_matches:
                # Remove duplicates preserving order
                seen = set()
                unique_matches = []
                for match in all_matches:
                    if match['value'] not in seen:
                        seen.add(match['value'])
                        unique_matches.append(match)
                
                matches[col_name] = {
                    'matches': unique_matches,
                    'example_values': col_data.get('values', [])[:5],
                    'likely_type': col_data.get('type', 'unknown')
                }
    
    return matches

def format_value_matches(value_matches):
    """Format value matches for the prompt template with error handling"""
    if not value_matches:
        return "No specific column values detected in the question."
    
    sections = []
    for col_name, match_data in value_matches.items():
        section = [f"### Column: {col_name}"]
        
        matches = match_data.get('matches', [])
        if not matches:
            section.append("No clear matches found.")
            continue
            
        high_conf = [m for m in matches if m.get('confidence') in ('high', 'medium')]
        if high_conf:
            section.append("Strong matches (use these preferentially):")
            for match in high_conf:
                section.append(f"- '{match.get('value', '')}' ({match.get('match_type', 'unknown')} match)")
        
        low_conf = [m for m in matches if m.get('confidence') == 'low']
        if low_conf:
            section.append("Possible matches (use with caution):")
            for match in low_conf:
                section.append(f"- '{match.get('value', '')}' ({match.get('match_type', 'unknown')} match)")
        
        sections.append("\n".join(section))
    
    return "\n\n".join(sections)

def preprocess_question(question: str, llm, schema_info: Dict) -> Tuple[str, Dict]:
    """
    Preprocess user questions with improved column value matching
    
    Args:
        question: User's natural language question
        llm: Initialized Gemini LLM instance
        schema_info: Database schema information
    
    Returns:
        Tuple of (processed_question, question_metadata)
    """
    # Find column value matches in the question
    value_matches = match_question_with_column_values(question, schema_info)
    
    # Create context about column values for the prompt
    columns_context = []
    for col_name, match_data in value_matches.items():
        match_info = []
        
        # Add information about exact matches
        high_confidence_matches = [m['value'] for m in match_data['matches'] 
                                 if m['confidence'] in ('high', 'medium')]
        
        if high_confidence_matches:
            match_info.append(f"Exact/strong matches: {', '.join(high_confidence_matches)}")
        
        # Add information about partial matches
        low_confidence_matches = [m['value'] for m in match_data['matches'] 
                                if m['confidence'] == 'low']
        
        if low_confidence_matches:
            match_info.append(f"Possible partial matches: {', '.join(low_confidence_matches)}")
            
        # Add examples of column values
        match_info.append(f"Other possible values: {', '.join(match_data['example_values'])}")
        
        # Combine info
        columns_context.append(
            f"Column '{col_name}':\n" + 
            "\n".join(f"  - {info}" for info in match_info)
        )
    
    value_match_info = "DETECTED COLUMN VALUES IN QUESTION:\n" + "\n".join(columns_context) if columns_context else ""
    
    # Extract key terms for context
    key_terms = re.findall(r'[\'"]([^\'"]+)[\'"]|(?:\b[A-Z][a-z]*\b){2,}|\b[A-Z][a-zA-Z0-9]+\b|\b[A-Z]+\b', question)
    key_terms = [term for term in key_terms if len(term) > 1]
    key_terms_str = ", ".join(key_terms) if key_terms else "None detected"
    
    preprocessing_prompt = f"""
    Analyze this question carefully: "{question}"
    
    Important key terms detected: {key_terms_str}
    
    {value_match_info}
    
    Return a JSON object with:
    {{
        "intent": "query type (aggregate, comparison, trend, list, etc.)",
        "metrics": ["numerical columns or calculations needed"],
        "filters": ["any conditions or constraints"],
        "time_range": "temporal context if any",
        "grouping": ["grouping dimensions if any"],
        "sorting": {{"column": "sort column", "order": "asc/desc"}},
        "limit": "number of results if specified",
        "column_filters": [
            {{
                "column": "column_name",
                "values": ["exact value to match"],
                "match_type": "exact|partial|contains",
                "confidence": "high|medium|low"
            }}
        ],
        "processed_question": "cleaned and standardized question"
    }}

    For column_filters, be very precise about the values. If a user asks for "Value" but a column contains "Value k EUR", 
    prefer the exact match "Value" if it exists, but propose "Value k EUR" only if there's strong evidence.

    Question: {question}
    """

    try:
        # Get LLM analysis
        response = llm.invoke(preprocessing_prompt)
        analysis = json.loads(response.content)

        # Extract metadata with enhanced column filters
        question_metadata = {
            'calculation_type': analysis.get('intent', ''),
            'metrics': analysis.get('metrics', []),
            'filters': analysis.get('filters', []),
            'time_context': analysis.get('time_range', ''),
            'grouping': analysis.get('grouping', []),
            'sorting': analysis.get('sorting', {}),
            'limit': analysis.get('limit', ''),
            'column_filters': analysis.get('column_filters', []),
            'raw_matches': value_matches
        }

        # Return processed question and metadata
        return analysis.get('processed_question', question), question_metadata
        
    except Exception as e:
        logger.error(f"Error preprocessing question: {str(e)}")
        return question, {'raw_matches': value_matches}  # Return original question and raw matches if error occurs

def generate_sql_query(question: str, schema_info: Dict) -> str:
    """
    Generate SQL query from natural language question
    """
    try:
        # Initialize LLM
        llm = initialize_llm()
        
        # Preprocess question
        processed_question, question_metadata = preprocess_question(question, llm, schema_info)
        
        # Format schema
        schema_str = generate_schema_string(schema_info)
        
        # Get relevant tables
        relevant_tables = extract_relevant_tables(processed_question, schema_info)
        
        # Format value matches for the prompt
        value_matches_str = format_value_matches(question_metadata.get('raw_matches', {}))
        
        # Get prompt template
        prompt_template = get_prompt_template()
        
        # Generate prompt
        prompt = prompt_template.format(
            question=processed_question,
            schema=schema_str,
            relevant_tables=relevant_tables,
            metadata=json.dumps(question_metadata, indent=2),
            value_matches=value_matches_str
        )
        
        # Generate SQL query
        response = llm.invoke(prompt)
        sql_query = response.content.strip()
        
        # Clean the query
        if '```sql' in sql_query:
            sql_query = sql_query.split('```sql')[1].split('```')[0].strip()
        elif '```' in sql_query:
            sql_query = sql_query.split('```')[1].split('```')[0].strip()
        
        return sql_query
        
    except Exception as e:
        logger.error(f"SQL query generation failed: {str(e)}")
        raise

def generate_schema_string(schema_info: Dict) -> str:
    """Generate formatted schema string with samples and relationships"""
    schema_str = []
    
    for table_name, table_data in schema_info.items():
        # Table header
        schema_str.append(f"### TABLE: {table_name}")
        
        # Columns with types
        schema_str.append("#### COLUMNS:")
        for col_name, col_type in table_data['columns']:
            schema_str.append(f"- {col_name} ({col_type})")
        
        # Foreign keys
        if table_data['foreign_keys']:
            schema_str.append("\n#### RELATIONSHIPS:")
            for fk in table_data['foreign_keys']:
                relation_str = f"- {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}"
                schema_str.append(relation_str)
        
        # Sample data
        if table_data['sample']:
            schema_str.append("\n#### SAMPLE DATA:")
            schema_str.append(str(table_data['sample']))
        
        schema_str.append("\n")
    
    return "\n".join(schema_str)

def validate_query(sql_query: str, schema_info: Dict) -> Tuple[bool, str]:
    """
    Validate the generated SQL query against the schema
    """
    # Check for common SQL injection patterns
    injection_patterns = [
        r';.*DROP',
        r';.*DELETE',
        r';.*UPDATE',
        r';.*INSERT',
        r';.*ALTER',
        r';.*CREATE',
        r';.*TRUNCATE',
        r'UNION.*SELECT'
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sql_query, re.IGNORECASE):
            return False, "Query contains potentially dangerous patterns"
    
    # Check for referenced tables
    tables_in_query = set()
    
    # Extract tables from FROM and JOIN clauses
    from_matches = re.finditer(r'\bFROM\s+([\w"]+(?:\s+AS\s+\w+)?)', sql_query, re.IGNORECASE)
    join_matches = re.finditer(r'\bJOIN\s+([\w"]+(?:\s+AS\s+\w+)?)', sql_query, re.IGNORECASE)
    
    for match in list(from_matches) + list(join_matches):
        table_ref = match.group(1)
        # Extract table name (removing alias if present)
        table_name = re.split(r'\s+AS\s+', table_ref, flags=re.IGNORECASE)[0]
        table_name = table_name.replace('"', '')
        tables_in_query.add(table_name)
    
    # Check each table exists
    for table in tables_in_query:
        if table not in schema_info:
            return False, f"Table '{table}' not found in database"
    
    # Check JOIN conditions
    if "JOIN" in sql_query.upper() and "ON" not in sql_query.upper():
        return False, "JOIN without ON condition detected"
    
    # Check for ambiguous columns in SELECT
    select_matches = re.finditer(r'\bSELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
    for match in select_matches:
        select_clause = match.group(1)
        columns = [col.strip() for col in select_clause.split(',')]
        
        for col in columns:
            # Check for unqualified columns when multiple tables are involved
            if len(tables_in_query) > 1 and '.' not in col and '*' not in col:
                # Check if this is a function or expression
                if not any(op in col.upper() for op in ['(', ')', 'AS', '||', '+', '-', '*', '/']):
                    return False, f"Ambiguous column '{col}' in SELECT with multiple tables"
    
    return True, "Validation passed"

def refine_query(original_query: str, error: str, schema_str: str, llm) -> str:
    """
    Attempt to fix a failed query using error feedback
    
    Args:
        original_query: The query that failed
        error: Error message from execution
        schema_str: Database schema information
        llm: Language model for refinement
        
    Returns:
        Refined SQL query
    """
    try:
        fix_prompt = f"""
The following SQL query failed with error: {error}

Original Query:
{original_query}

Database Schema:
{schema_str}

Please:
1. Analyze the error
2. Identify the problem
3. Provide a corrected query
4. Explain the changes made (briefly)

Return ONLY the corrected SQL query:
"""
        response = llm.invoke(fix_prompt)
        refined_query = response.content.strip()
        
        # Clean up the response
        if '```sql' in refined_query:
            refined_query = refined_query.split('```sql')[1].split('```')[0].strip()
        elif '```' in refined_query:
            refined_query = refined_query.split('```')[1].split('```')[0].strip()
            
        return refined_query
        
    except Exception as e:
        logger.error(f"Query refinement failed: {str(e)}")
        return original_query  # Return original if refinement fails