# analyzer.py

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
import json
import logging
from typing import Dict, List, Tuple, Optional, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

def generate_analysis_explanation(df: pd.DataFrame, user_question: str) -> str:
    """
    Generate comprehensive analysis of query results including:
    - Direct answer to user question
    - Key insights and trends
    - Statistical summaries
    - Data quality notes
    
    Args:
        df: Result DataFrame
        user_question: Original user question
        
    Returns:
        Formatted analysis string with markdown
    """
    if df.empty:
        return "### 📊 No Results Found\nThe query returned no data. Try modifying your search criteria."

    try:
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.0,
            google_api_key=settings.GOOGLE_API_KEY,
            convert_system_message_to_human=True
        )
        
        # Create statistical summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        
        stats_summary = []
        
        # Numeric column statistics
        if len(numeric_cols) > 0:
            stats = df[numeric_cols].agg(['count', 'mean', 'median', 'min', 'max', 'std']).round(2)
            for col in numeric_cols:
                non_null = df[col].count()
                null_pct = (df[col].isna().sum() / len(df)) * 100
                
                stats_summary.append(
                    f"- **{col}**:\n"
                    f"  - Valid values: {non_null:,} ({100-null_pct:.1f}% complete)\n"
                    f"  - Range: {stats.loc['min', col]:,} to {stats.loc['max', col]:,}\n"
                    f"  - Average: {stats.loc['mean', col]:,} (±{stats.loc['std', col]:,})\n"
                    f"  - Median: {stats.loc['median', col]:,}"
                )
        
        # Date range summary
        date_summary = []
        if date_cols:
            for col in date_cols:
                try:
                    # Check if the column contains actual datetime objects
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        min_date = df[col].min()
                        max_date = df[col].max()
                        date_summary.append(
                            f"- **{col}**: {min_date:%Y-%m-%d} to {max_date:%Y-%m-%d}"
                        )
                    else:
                        # For numeric columns that might be timestamps or non-date columns with 'date' in the name
                        min_val = df[col].min()
                        max_val = df[col].max()
                        # Try to convert to datetime if they appear to be timestamps
                        try:
                            min_date = pd.to_datetime(min_val)
                            max_date = pd.to_datetime(max_val)
                            date_summary.append(
                                f"- **{col}**: {min_date:%Y-%m-%d} to {max_date:%Y-%m-%d}"
                            )
                        except:
                            # If conversion fails, just display as numbers
                            date_summary.append(
                                f"- **{col}**: {min_val} to {max_val}"
                            )
                except Exception as e:
                    # Fallback for any other errors
                    logger.warning(f"Error processing date column {col}: {str(e)}")
                    date_summary.append(
                        f"- **{col}**: Unable to format date range"
                    )
        
        # Categorical summary 
        cat_summary = []
        if len(cat_cols) > 0:
            for col in cat_cols:
                unique_vals = df[col].nunique()
                top_vals = df[col].value_counts().head(3)
                cat_summary.append(
                    f"- **{col}**:\n"
                    f"  - {unique_vals:,} unique values\n"
                    f"  - Most common: {', '.join(f'{v} ({c:,})' for v, c in top_vals.items())}"
                )

        # Create analysis prompt
        analysis_prompt = f"""
You are a data analyst expert providing clear, actionable insights from SQL query results. Analyze this dataset with precision and depth.

CONTEXT:
The user asked: "{user_question}"

DATASET OVERVIEW:
- Records: {len(df):,}
- Time span: {date_summary[0] if date_summary else 'N/A'}
- Columns available: {', '.join(df.columns)}

KEY METRICS:
{chr(10).join(stats_summary) if stats_summary else "No numeric metrics available"}

CATEGORICAL BREAKDOWN:
{chr(10).join(cat_summary) if cat_summary else "No categorical data available"}

SAMPLE DATA (First 3 rows):
{df.head(3).to_string()}

YOUR ANALYSIS TASK:
1. Provide a concise, direct answer to the user's question with specific numbers and facts.
2. Highlight 2-3 significant patterns, trends, or insights visible in the data.
3. Point out any notable outliers, anomalies, or surprising findings.
4. Note any data quality concerns or limitations of this analysis.

FORMAT REQUIREMENTS:
- Use clear, professional language with specific numbers and percentages.
- Structure with descriptive headers and bullet points for readability.
- Start with a "Key Findings" section that directly answers the user's question.
- Include "Insights" and "Recommendations" sections.
- Keep your response concise (under 500 words) and focused on business value.
- Begin with "## Analysis Results" as the main heading.
"""
        
        # Get analysis from LLM
        try:
            response = llm.invoke(analysis_prompt)
            explanation = response.content if hasattr(response, 'content') else str(response)
            
            # Debug - log the first 200 chars of the response
            logger.info(f"LLM response received, length: {len(explanation)}, starts with: {explanation[:200]}")
            
            # Ensure it starts with a proper heading if not already present
            if not explanation.strip().startswith("## Analysis Results") and not explanation.strip().startswith("### Analysis Results"):
                explanation = f"## Analysis Results\n\n{explanation}"
        except Exception as llm_err:
            logger.error(f"LLM analysis generation error: {str(llm_err)}")
            explanation = "## Analysis Results\n\nUnable to generate detailed analysis. Please try reformulating your question."

        # Return the explanation
        return explanation

    except Exception as e:
        logger.error(f"Error generating analysis: {str(e)}")
        return f"## Analysis Results\n\nUnable to generate detailed analysis: {str(e)}"

def visualize_results(df: pd.DataFrame, question: str) -> Dict:
    """
    Generate appropriate visualizations based on:
    - Query results
    - Question context
    - Data types
    
    Args:
        df: Result DataFrame
        question: Original user question
        
    Returns:
        Dictionary of Plotly visualization JSON objects
    """
    if len(df) == 0:
        return {'error': 'No data available for visualization'}
    
    try:
        # Determine visualization type based on question and data
        date_cols = [col for col in df.columns if any(kw in str(col).lower() for kw in ['date', 'time', 'year', 'month'])]
        # Ensure date columns are actually date-like
        date_cols = [col for col in date_cols if pd.api.types.is_datetime64_any_dtype(df[col]) or 
                    (pd.api.types.is_numeric_dtype(df[col]) and col in date_cols)]
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        visualizations = {}
        
        # Make sure we only use the first 100 rows for visualization
        df_viz = df.head(100)
        
        # Time series visualization
        if len(date_cols) >= 1 and len(numeric_cols) >= 1:
            date_col = date_cols[0]
            value_col = numeric_cols[0]
            
            try:
                if 'trend' in question.lower() or 'over time' in question.lower():
                    # Format dates for better display if possible
                    if pd.api.types.is_datetime64_any_dtype(df_viz[date_col]):
                        # Convert to string for better display
                        df_viz_time = df_viz.copy()
                        df_viz_time[date_col] = df_viz_time[date_col].dt.strftime('%Y-%m-%d')
                    else:
                        df_viz_time = df_viz
                    
                    fig = px.line(df_viz_time, x=date_col, y=value_col, title=f"{value_col} Trend Over Time")
                    fig.update_xaxes(title_text=date_col)
                    fig.update_yaxes(title_text=value_col)
                    fig.update_layout(
                        autosize=True,
                        margin=dict(l=50, r=50, b=50, t=50, pad=4),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    visualizations['time_series'] = json.loads(pio.to_json(fig))
                else:
                    fig = px.bar(df_viz, x=date_col, y=value_col, title=f"{value_col} by {date_col}")
                    fig.update_xaxes(title_text=date_col)
                    fig.update_yaxes(title_text=value_col)
                    fig.update_layout(
                        autosize=True,
                        margin=dict(l=50, r=50, b=50, t=50, pad=4),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    visualizations['bar_chart'] = json.loads(pio.to_json(fig))
            except Exception as e:
                logger.warning(f"Failed to create time series visualization: {str(e)}")
        
        # Categorical visualization
        if len(cat_cols) >= 1 and len(numeric_cols) >= 1:
            cat_col = cat_cols[0]
            value_col = numeric_cols[0]
            
            try:
                # Limit categories to top 10 for better visualization
                top_categories = df_viz[cat_col].value_counts().nlargest(10).index.tolist()
                df_viz_cat = df_viz[df_viz[cat_col].isin(top_categories)]
                
                if 'distribution' in question.lower() or 'frequency' in question.lower():
                    fig = px.histogram(df_viz_cat, x=cat_col, y=value_col, 
                                      title=f"Distribution of {value_col} by {cat_col}")
                    fig.update_layout(
                        autosize=True,
                        margin=dict(l=50, r=50, b=50, t=50, pad=4),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    visualizations['histogram'] = json.loads(pio.to_json(fig))
                elif 'compare' in question.lower() or 'ranking' in question.lower():
                    # Create aggregated data for better visualization
                    agg_df = df_viz_cat.groupby(cat_col)[value_col].sum().reset_index()
                    agg_df = agg_df.sort_values(value_col, ascending=False)
                    
                    fig = px.bar(agg_df, x=cat_col, y=value_col, 
                                title=f"Comparison of {value_col} by {cat_col}")
                    fig.update_layout(
                        autosize=True,
                        margin=dict(l=50, r=50, b=50, t=50, pad=4),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    visualizations['bar_chart'] = json.loads(pio.to_json(fig))
                else:
                    # Make sure we don't have too many categories for a pie chart
                    if df_viz_cat[cat_col].nunique() <= 15:  # Limit to 15 categories for pie charts
                        # Create aggregated data for pie chart
                        agg_df = df_viz_cat.groupby(cat_col)[value_col].sum().reset_index()
                        
                        fig = px.pie(agg_df, names=cat_col, values=value_col, 
                                    title=f"Proportion of {value_col} by {cat_col}")
                        fig.update_layout(
                            autosize=True,
                            margin=dict(l=50, r=50, b=50, t=50, pad=4),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        )
                        visualizations['pie_chart'] = json.loads(pio.to_json(fig))
                    else:
                        # Too many categories, use a bar chart instead
                        top_cats = df_viz_cat.groupby(cat_col)[value_col].sum().nlargest(10).index
                        filtered_df = df_viz_cat[df_viz_cat[cat_col].isin(top_cats)]
                        fig = px.bar(filtered_df, x=cat_col, y=value_col, 
                                    title=f"Top 10 {cat_col} by {value_col}")
                        fig.update_layout(
                            autosize=True,
                            margin=dict(l=50, r=50, b=50, t=50, pad=4),
                        )
                        visualizations['bar_chart'] = json.loads(pio.to_json(fig))
            except Exception as e:
                logger.warning(f"Failed to create categorical visualization: {str(e)}")
        
        # Correlation analysis
        if len(numeric_cols) >= 2:
            try:
                if 'relation' in question.lower() or 'correlation' in question.lower():
                    # Limit to first 4 numeric columns for readability
                    num_subset = numeric_cols[:4]
                    fig = px.scatter_matrix(df_viz, dimensions=num_subset, title="Correlation Analysis")
                    fig.update_layout(
                        autosize=True,
                        margin=dict(l=50, r=50, b=50, t=50, pad=4),
                    )
                    visualizations['scatter_matrix'] = json.loads(pio.to_json(fig))
                else:
                    fig = px.scatter(df_viz, x=numeric_cols[0], y=numeric_cols[1], 
                                   title=f"{numeric_cols[1]} vs {numeric_cols[0]}")
                    fig.update_layout(
                        autosize=True,
                        margin=dict(l=50, r=50, b=50, t=50, pad=4),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    visualizations['scatter'] = json.loads(pio.to_json(fig))
            except Exception as e:
                logger.warning(f"Failed to create correlation visualization: {str(e)}")
        
        # If no specific visualization was created, add simplified data for table view
        if not visualizations:
            visualizations['table'] = df.head(10).to_dict(orient='records')
        
        logger.info(f"Generated {len(visualizations)} visualizations")
        return visualizations
        
    except Exception as e:
        logger.error(f"Visualization error: {str(e)}")
        return {'error': f'Failed to generate visualization: {str(e)}'}