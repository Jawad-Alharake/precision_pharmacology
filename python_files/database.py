"""
Phase 2: Relational Database Architecture
Build and manage SQLite database for genetic signatures and compound metadata.
"""

import sqlite3
import pandas as pd
import logging
import config
from logger import setup_logger


logger = setup_logger(__name__)


def create_database(db_path=None):
    """
    Create SQLite database connection.
    
    Args:
        db_path (str): Path to database file. Defaults to config.DATABASE_FILE.
    
    Returns:
        sqlite3.Connection: Database connection.
    """
    if db_path is None:
        db_path = config.DATABASE_FILE
    
    logger.info(f"Creating/connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    logger.info(f"✓ Database connection established")
    
    return conn


def create_schema(conn):
    """
    Create database schema with appropriate tables and indexes.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    """
    logger.info("Creating database schema...")
    cursor = conn.cursor()
    
    # Compound metadata table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compound_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pert_iname TEXT UNIQUE NOT NULL,
            moa TEXT,
            target TEXT,
            canonical_smiles TEXT,
            pubchem_cid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_compound UNIQUE(pert_iname)
        )
    ''')
    logger.info("✓ Created compound_metadata table")
    
    # Genetic signatures table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS genetic_signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pert_iname TEXT NOT NULL,
            pr_gene_symbol TEXT NOT NULL,
            z_score REAL NOT NULL,
            is_significant INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pert_iname) REFERENCES compound_metadata(pert_iname),
            CONSTRAINT unique_signature UNIQUE(pert_iname, pr_gene_symbol)
        )
    ''')
    logger.info("✓ Created genetic_signatures table")
    
    conn.commit()


def create_indexes(conn):
    """
    Create indexes for query optimization.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    """
    logger.info("Creating database indexes...")
    cursor = conn.cursor()
    
    indexes = [
        ('idx_pert_iname', 'genetic_signatures', 'pert_iname'),
        ('idx_gene_symbol', 'genetic_signatures', 'pr_gene_symbol'),
        ('idx_z_score', 'genetic_signatures', 'z_score'),
        ('idx_is_significant', 'genetic_signatures', 'is_significant'),
        ('idx_compound_moa', 'compound_metadata', 'moa'),
    ]
    
    for idx_name, table, column in indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})')
            logger.info(f"✓ Created index {idx_name}")
        except sqlite3.OperationalError as e:
            logger.warning(f"Index {idx_name} already exists or error: {e}")
    
    conn.commit()


def ingest_compound_metadata(conn, compound_df):
    """
    Ingest compound metadata into database.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        compound_df (pd.DataFrame): Compound metadata dataframe.
    """
    logger.info(f"Ingesting {len(compound_df)} compound records...")
    
    try:
        compound_df.to_sql('compound_metadata', conn, if_exists='append', index=False)
        logger.info(f"✓ Successfully ingested compound metadata")
    except sqlite3.IntegrityError as e:
        logger.warning(f"Some compounds already exist in database: {e}")
    except Exception as e:
        logger.error(f"Error ingesting compound metadata: {e}")
        raise


def ingest_genetic_signatures(conn, signature_df, chunk_size=None):
    """
    Ingest genetic signatures into database in chunks for memory efficiency.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        signature_df (pd.DataFrame): Genetic signatures dataframe.
        chunk_size (int): Number of rows per chunk. Defaults to config.DB_CHUNK_SIZE.
    """
    if chunk_size is None:
        chunk_size = config.DB_CHUNK_SIZE
    
    total_rows = len(signature_df)
    logger.info(f"Ingesting {total_rows} genetic signature records in chunks of {chunk_size}...")
    
    # Mark significant hits
    signature_df['is_significant'] = (
        (signature_df['z_score'] >= config.Z_SCORE_THRESHOLD) | 
        (signature_df['z_score'] <= -config.Z_SCORE_THRESHOLD)
    ).astype(int)
    
    try:
        for i in range(0, total_rows, chunk_size):
            chunk = signature_df[i:i+chunk_size]
            chunk.to_sql('genetic_signatures', conn, if_exists='append', index=False)
            
            if (i + chunk_size) % (chunk_size * 10) == 0:
                logger.info(f"  Processed {i + chunk_size}/{total_rows} records ({(i + chunk_size)/total_rows*100:.1f}%)")
        
        logger.info(f"✓ Successfully ingested all genetic signatures")
    
    except sqlite3.IntegrityError as e:
        logger.warning(f"Some signatures already exist in database: {e}")
    except Exception as e:
        logger.error(f"Error ingesting genetic signatures: {e}")
        raise
    
    conn.commit()


def verify_data_integrity(conn):
    """
    Verify database integrity and report statistics.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    
    Returns:
        dict: Integrity report.
    """
    logger.info("Verifying database integrity...")
    cursor = conn.cursor()
    
    report = {}
    
    # Count compounds
    cursor.execute('SELECT COUNT(*) FROM compound_metadata')
    report['compound_count'] = cursor.fetchone()[0]
    
    # Count signatures
    cursor.execute('SELECT COUNT(*) FROM genetic_signatures')
    report['signature_count'] = cursor.fetchone()[0]
    
    # Count significant signatures
    cursor.execute('SELECT COUNT(*) FROM genetic_signatures WHERE is_significant = 1')
    report['significant_count'] = cursor.fetchone()[0]
    
    # Check for orphaned signatures (should not exist with proper FK)
    cursor.execute('''
        SELECT COUNT(*) FROM genetic_signatures 
        WHERE pert_iname NOT IN (SELECT pert_iname FROM compound_metadata)
    ''')
    report['orphaned_signatures'] = cursor.fetchone()[0]
    
    logger.info(f"\nDatabase Integrity Report:")
    logger.info(f"  Total compounds: {report['compound_count']}")
    logger.info(f"  Total signatures: {report['signature_count']}")
    logger.info(f"  Significant signatures: {report['significant_count']} ({report['significant_count']/report['signature_count']*100:.2f}%)")
    logger.info(f"  Orphaned signatures: {report['orphaned_signatures']}")
    
    if report['orphaned_signatures'] > 0:
        logger.warning(f"⚠ Found {report['orphaned_signatures']} orphaned signatures!")
    
    return report


def execute_query(conn, query):
    """
    Execute a SQL query and return results as DataFrame.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        query (str): SQL query.
    
    Returns:
        pd.DataFrame: Query results.
    """
    try:
        result = pd.read_sql_query(query, conn)
        logger.debug(f"Query executed successfully, returned {len(result)} rows")
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise


def close_database(conn):
    """
    Close database connection.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    """
    if conn:
        conn.close()
        logger.info("Database connection closed")
