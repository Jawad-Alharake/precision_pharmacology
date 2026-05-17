"""
Phase 3: Business Analytics & Insight Generation
SQL-based analytics queries for drug candidate identification and ranking.
"""

import pandas as pd
import logging
import config
from logger import setup_logger


logger = setup_logger(__name__)


# SQL Queries for business analytics
BUSINESS_QUERIES = {
    'reversal_of_disease_signatures': '''
        SELECT m.pert_iname, AVG(s.z_score) as avg_impact
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        WHERE s.pr_gene_symbol IN ('DDIT4', 'PSME1')
        AND s.z_score > 2.0
        GROUP BY m.pert_iname
        HAVING COUNT(DISTINCT s.pr_gene_symbol) = 2
        ORDER BY avg_impact DESC
        LIMIT 10
    ''',
    
    'mechanism_of_action_discovery': '''
        SELECT m.pert_iname, m.moa, COUNT(*) as matching_gene_count
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        WHERE s.pr_gene_symbol IN (
            SELECT pr_gene_symbol FROM genetic_signatures 
            WHERE pert_iname = 'bortezomib' AND z_score > 3.0
        )
        AND s.z_score > 3.0
        AND m.pert_iname != 'bortezomib'
        GROUP BY m.pert_iname, m.moa
        ORDER BY matching_gene_count DESC
        LIMIT 10
    ''',
    
    'safety_and_toxicity_prediction': '''
        SELECT m.pert_iname, COUNT(*) as extreme_hit_count
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        WHERE abs(s.z_score) > 4.0
        GROUP BY m.pert_iname
        ORDER BY extreme_hit_count DESC
        LIMIT 20
    ''',
    
    'drug_potency_benchmarking': '''
        SELECT m.pert_iname, m.moa, MAX(abs(s.z_score)) as max_potency
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        GROUP BY m.pert_iname, m.moa
        ORDER BY max_potency DESC
        LIMIT 10
    ''',
    
    'master_regulator_genes': '''
        SELECT s.pr_gene_symbol, COUNT(*) as frequency
        FROM genetic_signatures s
        WHERE abs(s.z_score) > 2.0
        GROUP BY s.pr_gene_symbol
        ORDER BY frequency DESC
        LIMIT 15
    ''',
    
    'repurposing_efficiency': '''
        SELECT m.pert_iname, m.moa, COUNT(DISTINCT s.pr_gene_symbol) as genes_regulated
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        WHERE m.pert_iname NOT LIKE 'BRD-%' 
        AND abs(s.z_score) > 3.0
        GROUP BY m.pert_iname, m.moa
        ORDER BY genes_regulated DESC
        LIMIT 10
    ''',
    
    'precision_vs_power': '''
        SELECT m.pert_iname, 
               MAX(abs(s.z_score)) as max_potency, 
               COUNT(DISTINCT s.pr_gene_symbol) as affected_genes
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        GROUP BY m.pert_iname
    ''',
    
    'therapeutic_class_validation': '''
        SELECT m.pert_iname, m.moa, s.pr_gene_symbol, AVG(s.z_score) as avg_z
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        WHERE s.pr_gene_symbol IN ('DDIT4', 'HSPA5')
        GROUP BY m.pert_iname, m.moa, s.pr_gene_symbol
        HAVING avg_z > 4.0
        ORDER BY m.pert_iname
    ''',
    
    'top_10_precision_leads': '''
        SELECT m.pert_iname, 
               m.moa,
               m.canonical_smiles,
               m.pubchem_cid,
               MAX(abs(s.z_score)) as max_potency, 
               COUNT(DISTINCT s.pr_gene_symbol) as total_gene_hits
        FROM compound_metadata m
        JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
        GROUP BY m.pert_iname, m.moa, m.canonical_smiles, m.pubchem_cid
        HAVING total_gene_hits <= 50 AND max_potency >= 8.0
        ORDER BY max_potency DESC
        LIMIT 10
    '''
}


def run_business_query(conn, query_name):
    """
    Execute a predefined business analytics query.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        query_name (str): Name of query from BUSINESS_QUERIES.
    
    Returns:
        pd.DataFrame: Query results.
    """
    if query_name not in BUSINESS_QUERIES:
        logger.error(f"Query '{query_name}' not found in BUSINESS_QUERIES")
        raise ValueError(f"Unknown query: {query_name}")
    
    logger.info(f"Executing business query: {query_name}")
    
    try:
        query = BUSINESS_QUERIES[query_name]
        result = pd.read_sql_query(query, conn)
        logger.info(f"✓ Query returned {len(result)} results")
        return result
    
    except Exception as e:
        logger.error(f"Error executing query '{query_name}': {e}")
        raise


def get_top_precision_leads_detailed(conn):
    """
    Get top 10 precision leads with detailed gene information.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    
    Returns:
        tuple: (summary_df, detailed_df)
    """
    logger.info("Fetching top 10 precision leads with detailed analysis...")
    
    # Get summary
    summary_query = BUSINESS_QUERIES['top_10_precision_leads']
    summary = pd.read_sql_query(summary_query, conn)
    logger.info(f"Found {len(summary)} precision leads")
    
    # Get detailed gene hits for each lead
    if len(summary) > 0:
        leads_list = "', '".join(summary['pert_iname'].astype(str))
        
        detailed_query = f'''
            SELECT m.pert_iname, m.moa, s.pr_gene_symbol, s.z_score
            FROM compound_metadata m
            JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
            WHERE m.pert_iname IN ('{leads_list}')
            AND abs(s.z_score) >= {config.Z_SCORE_THRESHOLD}
            ORDER BY m.pert_iname, ABS(s.z_score) DESC
        '''
        
        detailed = pd.read_sql_query(detailed_query, conn)
        logger.info(f"Retrieved {len(detailed)} detailed gene-level records")
        
        return summary, detailed
    
    return summary, pd.DataFrame()


def get_gene_statistics(conn):
    """
    Get statistics about gene involvement across all compounds.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    
    Returns:
        pd.DataFrame: Gene statistics.
    """
    logger.info("Computing gene statistics...")
    
    query = '''
        SELECT 
            pr_gene_symbol,
            COUNT(DISTINCT pert_iname) as compound_count,
            AVG(ABS(z_score)) as avg_abs_z_score,
            MAX(ABS(z_score)) as max_abs_z_score,
            MIN(ABS(z_score)) as min_abs_z_score,
            COUNT(*) as total_occurrences
        FROM genetic_signatures
        WHERE is_significant = 1
        GROUP BY pr_gene_symbol
        ORDER BY total_occurrences DESC
    '''
    
    result = pd.read_sql_query(query, conn)
    logger.info(f"Gene statistics computed for {len(result)} genes")
    
    return result


def export_results(summary_df, detailed_df, summary_path=None, detailed_path=None):
    """
    Export analytics results to CSV files.
    
    Args:
        summary_df (pd.DataFrame): Summary results.
        detailed_df (pd.DataFrame): Detailed results.
        summary_path (str): Path for summary CSV. Defaults to config value.
        detailed_path (str): Path for detailed CSV. Defaults to config value.
    """
    if summary_path is None:
        summary_path = config.TOP_10_LEADS_SUMMARY
    if detailed_path is None:
        detailed_path = config.TOP_10_DETAILED_GENES
    
    logger.info(f"Exporting results to CSV files...")
    
    # Export summary
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"✓ Exported summary to {summary_path}")
    
    # Export detailed
    detailed_df.to_csv(detailed_path, index=False)
    logger.info(f"✓ Exported detailed results to {detailed_path}")


def get_compound_profile(conn, compound_name):
    """
    Get complete profile for a specific compound.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        compound_name (str): Compound identifier (pert_iname).
    
    Returns:
        dict: Complete compound profile.
    """
    logger.info(f"Retrieving profile for compound: {compound_name}")
    
    # Get metadata
    metadata_query = f"SELECT * FROM compound_metadata WHERE pert_iname = '{compound_name}'"
    metadata = pd.read_sql_query(metadata_query, conn)
    
    # Get gene signatures
    signature_query = f'''
        SELECT * FROM genetic_signatures 
        WHERE pert_iname = '{compound_name}' 
        ORDER BY ABS(z_score) DESC
    '''
    signatures = pd.read_sql_query(signature_query, conn)
    
    profile = {
        'metadata': metadata,
        'signatures': signatures,
        'significant_hits': len(signatures[signatures['is_significant'] == 1]),
        'total_affected_genes': len(signatures)
    }
    
    return profile
