"""
Pipeline Orchestrator for Precision Pharmacology.
Coordinates execution of all phases with error tracking and reporting.
"""

from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import pandas as pd
import sqlite3
import config
from logger import setup_logger
from exceptions import PrecisionPharmacologyError

# Import phase modules
import data_extraction
import database
import analytics
import web_scraper
import phase_5_analysis


logger = setup_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates execution of all pipeline phases."""
    
    def __init__(self):
        """Initialize the pipeline orchestrator."""
        self.phases = {}
        self.errors = {}
        self.start_time = None
        self.end_time = None
        self.execution_report = {}
        logger.info("Pipeline Orchestrator initialized")
    
    def run_phase_1_extraction(self, gctx_path: str, metadata_paths: Dict[str, str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run Phase 1: Data Extraction & Dimensionality Reduction.
        
        Args:
            gctx_path (str): Path to GCTX file.
            metadata_paths (dict): Paths to metadata files.
        
        Returns:
            tuple: (compound_metadata, genetic_signatures)
        """
        phase_name = "Phase 1: Data Extraction"
        logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        
        try:
            # Parse GCTX file
            gctx_data = data_extraction.parse_gctx_file(gctx_path)
            
            # Parse metadata files
            gene_metadata = data_extraction.parse_metadata_file(metadata_paths.get('gene'), compression='gzip')
            pert_info = data_extraction.parse_metadata_file(metadata_paths.get('pert'), compression='gzip')
            
            # Validate data quality
            data_extraction.validate_data_quality(gctx_data, "GCTX Data")
            
            # Filter by Z-score
            filtered_data = data_extraction.filter_by_z_score(gctx_data)
            
            # Create compound metadata
            compound_metadata = data_extraction.create_compound_metadata(pert_info, gene_metadata)
            
            # Melt to long format
            genetic_signatures = data_extraction.melt_wide_to_long(filtered_data, id_vars=['pert_iname'])
            
            # Remove duplicates
            genetic_signatures = data_extraction.remove_duplicates(genetic_signatures, 
                                                                   subset=['pert_iname', 'gene'])
            
            # Save processed data
            data_extraction.save_processed_data(compound_metadata, genetic_signatures)
            
            self.phases['phase_1'] = {
                'status': 'success',
                'compounds': len(compound_metadata),
                'signatures': len(genetic_signatures)
            }
            
            logger.info(f"✓ Phase 1 Complete: {len(compound_metadata)} compounds, {len(genetic_signatures)} signatures")
            return compound_metadata, genetic_signatures
        
        except Exception as e:
            self.errors['phase_1'] = str(e)
            logger.error(f"✗ Phase 1 Failed: {e}")
            raise
    
    def run_phase_2_database(self, compound_data: pd.DataFrame, 
                            signature_data: pd.DataFrame) -> sqlite3.Connection:
        """
        Run Phase 2: Relational Database Architecture.
        
        Args:
            compound_data (pd.DataFrame): Compound metadata.
            signature_data (pd.DataFrame): Genetic signatures.
        
        Returns:
            sqlite3.Connection: Database connection.
        """
        phase_name = "Phase 2: Database Architecture"
        logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        
        try:
            # Create database
            conn = database.create_database()
            
            # Create schema
            database.create_schema(conn)
            
            # Create indexes
            database.create_indexes(conn)
            
            # Ingest data
            database.ingest_compound_metadata(conn, compound_data)
            database.ingest_genetic_signatures(conn, signature_data)
            
            # Verify integrity
            integrity_report = database.verify_data_integrity(conn)
            
            self.phases['phase_2'] = {
                'status': 'success',
                'compounds_ingested': integrity_report['compound_count'],
                'signatures_ingested': integrity_report['signature_count']
            }
            
            logger.info(f"✓ Phase 2 Complete: Database ready with {integrity_report['compound_count']} compounds")
            return conn
        
        except Exception as e:
            self.errors['phase_2'] = str(e)
            logger.error(f"✗ Phase 2 Failed: {e}")
            raise
    
    def run_phase_3_analytics(self, conn: sqlite3.Connection) -> Dict:
        """
        Run Phase 3: Business Analytics.
        
        Args:
            conn (sqlite3.Connection): Database connection.
        
        Returns:
            dict: Analytics results.
        """
        phase_name = "Phase 3: Business Analytics"
        logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        
        try:
            # Run analytics queries
            results = {}
            for query_name in analytics.BUSINESS_QUERIES.keys():
                result = analytics.run_business_query(conn, query_name)
                results[query_name] = result
            
            # Get top precision leads
            summary, detailed = analytics.get_top_precision_leads_detailed(conn)
            results['top_leads_summary'] = summary
            results['top_leads_detailed'] = detailed
            
            # Export results
            analytics.export_results(summary, detailed)
            
            self.phases['phase_3'] = {
                'status': 'success',
                'queries_run': len(analytics.BUSINESS_QUERIES),
                'top_leads': len(summary)
            }
            
            logger.info(f"✓ Phase 3 Complete: {len(summary)} precision leads identified")
            return results
        
        except Exception as e:
            self.errors['phase_3'] = str(e)
            logger.error(f"✗ Phase 3 Failed: {e}")
            raise
    
    def run_phase_4_scraping(self, compound_names: List[str]) -> pd.DataFrame:
        """
        Run Phase 4: Literature Footprint & Risk Assessment.
        
        Args:
            compound_names (list): List of compound names to search.
        
        Returns:
            pd.DataFrame: Novelty assessment results.
        """
        phase_name = "Phase 4: Literature Footprint & Risk Assessment"
        logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        
        try:
            # Initialize scraper
            scraper = web_scraper.PubMedScraper()
            
            # Batch search
            results = scraper.batch_search(compound_names)
            
            # Generate report
            report = web_scraper.generate_novelty_report(results)
            
            # Close scraper
            scraper.close()
            
            self.phases['phase_4'] = {
                'status': 'success',
                'compounds_searched': len(results),
                'novel_compounds': (results['novelty_status'] == 'novel').sum()
            }
            
            logger.info(f"✓ Phase 4 Complete: {len(results)} compounds assessed for novelty")
            return report
        
        except Exception as e:
            self.errors['phase_4'] = str(e)
            logger.error(f"✗ Phase 4 Failed: {e}")
            raise
    
    def run_phase_5_temporal_analysis(self, conn: sqlite3.Connection) -> pd.DataFrame:
        """
        Run Phase 5: Temporal Pharmacodynamics & Clinical Profile Classification.
        
        Args:
            conn (sqlite3.Connection): Database connection.
        
        Returns:
            pd.DataFrame: Clinical profiles with temporal analysis.
        """
        phase_name = "Phase 5: Temporal Pharmacodynamics & Clinical Analysis"
        logger.info(f"\n{'='*80}\n{phase_name}\n{'='*80}")
        
        try:
            # Extract temporal features
            features = phase_5_analysis.extract_temporal_features(conn)
            
            # Classify clinical profiles
            profiles = phase_5_analysis.classify_clinical_profiles(features, use_ml=True)
            
            # Generate report
            report = phase_5_analysis.generate_temporal_report(profiles)
            
            self.phases['phase_5'] = {
                'status': 'success',
                'compounds_analyzed': len(profiles),
                'profile_distribution': profiles['clinical_profile'].value_counts().to_dict()
            }
            
            logger.info(f"✓ Phase 5 Complete: Clinical profiles classified for {len(profiles)} compounds")
            return report
        
        except Exception as e:
            self.errors['phase_5'] = str(e)
            logger.error(f"✗ Phase 5 Failed: {e}")
            raise
    
    def run_full_pipeline(self, gctx_path: str, metadata_paths: Dict[str, str]) -> Dict:
        """
        Run complete pipeline (Phases 1-5).
        
        Args:
            gctx_path (str): Path to GCTX file.
            metadata_paths (dict): Paths to metadata files.
        
        Returns:
            dict: Full execution report.
        """
        self.start_time = datetime.now()
        logger.info(f"\n{'#'*80}\nPRECISION PHARMACOLOGY PIPELINE START\n{'#'*80}")
        logger.info(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            # Phase 1
            compound_data, signature_data = self.run_phase_1_extraction(gctx_path, metadata_paths)
            
            # Phase 2
            conn = self.run_phase_2_database(compound_data, signature_data)
            
            # Phase 3
            analytics_results = self.run_phase_3_analytics(conn)
            
            # Phase 4
            top_compounds = compound_data['pert_iname'].head(20).tolist()
            novelty_report = self.run_phase_4_scraping(top_compounds)
            
            # Phase 5
            temporal_report = self.run_phase_5_temporal_analysis(conn)
            
            # Close database
            database.close_database(conn)
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            self._generate_execution_report(duration)
            return self.execution_report
        
        except Exception as e:
            logger.error(f"\n✗ PIPELINE FAILED: {e}")
            self.end_time = datetime.now()
            raise
        finally:
            logger.info(f"\n{'#'*80}\nPRECISION PHARMACOLOGY PIPELINE END\n{'#'*80}\n")
    
    def _generate_execution_report(self, duration: float) -> None:
        """Generate final execution report."""
        self.execution_report = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': duration,
            'phases': self.phases,
            'errors': self.errors,
            'status': 'success' if not self.errors else 'failed',
            'total_phases_run': len(self.phases),
            'total_phases_failed': len(self.errors)
        }
        
        logger.info("\n" + "="*80)
        logger.info("EXECUTION REPORT")
        logger.info("="*80)
        logger.info(f"Status: {self.execution_report['status'].upper()}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Phases Completed: {len(self.phases)}")
        logger.info(f"Phases Failed: {len(self.errors)}")
        
        for phase, result in self.phases.items():
            logger.info(f"✓ {phase}: {result}")
        
        for phase, error in self.errors.items():
            logger.error(f"✗ {phase}: {error}")
