"""
Phase 2: Relational Database Architecture
Build and manage SQLite database for genetic signatures and compound metadata.
"""

from typing import Optional, Dict, Tuple
import sqlite3
import pandas as pd
import logging
import config
from logger import setup_logger
from exceptions import DatabaseError


logger = setup_logger(__name__)


def create_database(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create SQLite database connection.
    
    Args:
        db_path (str): Path to database file. Defaults to config.DATABASE_FILE.
    
    Returns:
        sqlite3.Connection: Database connection.
        
    Raises:
        DatabaseError: If connection fails.
    """
    if db_path is None:
        db_path = config.DATABASE_FILE
    
    try:
        logger.info(f"Creating/connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        logger.info(f"✓ Database connection established")
        return conn
    except Exception as e:
        logger.error(f"Failed to create database connection: {e}")
        raise DatabaseError(f"Failed to create database: {e}")


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create database schema with appropriate tables and indexes.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        
    Raises:
        DatabaseError: If schema creation fails.
    """
    logger.info("Creating database schema...")
    cursor = conn.cursor()
    
    try:
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
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        raise DatabaseError(f"Failed to create schema: {e}")


def create_indexes(conn: sqlite3.Connection) -> None:
    """
    Create indexes for query optimization.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        
    Raises:
        DatabaseError: If index creation fails.
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
    
    try:
        for idx_name, table, column in indexes:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})')
            logger.info(f"✓ Created index {idx_name}")
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.warning(f"Index creation warning: {e}")


def ingest_compound_metadata(conn: sqlite3.Connection, compound_df: pd.DataFrame) -> int:
    """
    Ingest compound metadata into database.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        compound_df (pd.DataFrame): Compound metadata dataframe.
    
    Returns:
        int: Number of records ingested.
        
    Raises:
        DatabaseError: If ingestion fails.
    """
    if compound_df is None or len(compound_df) == 0:
        raise DatabaseError("Compound dataframe is empty or None")
    
    logger.info(f"Ingesting {len(compound_df)} compound records...")
    
    try:
        compound_df.to_sql('compound_metadata', conn, if_exists='append', index=False)
        conn.commit()
        logger.info(f"✓ Successfully ingested {len(compound_df)} compound records")
        return len(compound_df)
    except sqlite3.IntegrityError as e:
        logger.warning(f"Some compounds already exist in database: {e}")
        return 0
    except Exception as e:
        logger.error(f"Error ingesting compound metadata: {e}")
        raise DatabaseError(f"Failed to ingest compound metadata: {e}")


def ingest_genetic_signatures(conn: sqlite3.Connection, signature_df: pd.DataFrame, 
                             chunk_size: Optional[int] = None) -> int:
    """
    Ingest genetic signatures into database in chunks for memory efficiency.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        signature_df (pd.DataFrame): Genetic signatures dataframe.
        chunk_size (int): Number of rows per chunk. Defaults to config.DB_CHUNK_SIZE.
    
    Returns:
        int: Number of records ingested.
        
    Raises:
        DatabaseError: If ingestion fails.
    """
    if signature_df is None or len(signature_df) == 0:
        raise DatabaseError("Signature dataframe is empty or None")
    
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
        ingested_count = 0
        for i in range(0, total_rows, chunk_size):
            chunk = signature_df[i:i+chunk_size]
            chunk.to_sql('genetic_signatures', conn, if_exists='append', index=False)
            ingested_count += len(chunk)
            
            if (i + chunk_size) % (chunk_size * 10) == 0:
                logger.info(f"  Processed {i + chunk_size}/{total_rows} records ({(i + chunk_size)/total_rows*100:.1f}%)")
        
        conn.commit()
        logger.info(f"✓ Successfully ingested {ingested_count} genetic signatures")
        return ingested_count
    
    except sqlite3.IntegrityError as e:
        logger.warning(f"Some signatures already exist in database: {e}")
        return 0
    except Exception as e:
        logger.error(f"Error ingesting genetic signatures: {e}")
        raise DatabaseError(f"Failed to ingest genetic signatures: {e}")


def verify_data_integrity(conn: sqlite3.Connection) -> Dict:
    """
    Verify database integrity and report statistics.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    
    Returns:
        dict: Integrity report.
        
    Raises:
        DatabaseError: If verification fails.
    """
    logger.info("Verifying database integrity...")
    cursor = conn.cursor()
    
    try:
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
        
        # Calculate percentages
        report['significant_percentage'] = (
            report['significant_count'] / report['signature_count'] * 100 
            if report['signature_count'] > 0 else 0
        )
        
        logger.info(f"\nDatabase Integrity Report:")
        logger.info(f"  Total compounds: {report['compound_count']}")
        logger.info(f"  Total signatures: {report['signature_count']}")
        logger.info(f"  Significant signatures: {report['significant_count']} ({report['significant_percentage']:.2f}%)")
        logger.info(f"  Orphaned signatures: {report['orphaned_signatures']}")
        
        if report['orphaned_signatures'] > 0:
            logger.warning(f"⚠ Found {report['orphaned_signatures']} orphaned signatures!")
        
        return report
    
    except Exception as e:
        logger.error(f"Error verifying database integrity: {e}")
        raise DatabaseError(f"Failed to verify integrity: {e}")


def execute_query(conn: sqlite3.Connection, query: str) -> pd.DataFrame:
    """
    Execute a SQL query and return results as DataFrame.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        query (str): SQL query.
    
    Returns:
        pd.DataFrame: Query results.
        
    Raises:
        DatabaseError: If query execution fails.
    """
    try:
        result = pd.read_sql_query(query, conn)
        logger.debug(f"Query executed successfully, returned {len(result)} rows")
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise DatabaseError(f"Failed to execute query: {e}")


def close_database(conn: sqlite3.Connection) -> None:
    """
    Close database connection.
    
    Args:
        conn (sqlite3.Connection): Database connection.
    """
    try:
        if conn:
            conn.close()
            logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
