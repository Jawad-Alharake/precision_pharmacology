"""
Configuration parameters for the Precision Pharmacology pipeline.
Centralized settings for easy adjustment without modifying notebook cells.
"""

# Data Processing Thresholds
Z_SCORE_THRESHOLD = 2.0  # Minimum Z-score to consider a gene as significantly affected
EXTREME_Z_SCORE = 4.0  # Z-score threshold for identifying potential toxicity/extreme effects
POTENCY_THRESHOLD = 3.0  # Z-score threshold for identifying potent compounds

# Drug Selection Criteria
TOP_N_LEADS = 10  # Number of top precision leads to identify
MAX_AFFECTED_GENES = 50  # Maximum number of genes a "surgical" drug should affect
MIN_POTENCY = 8.0  # Minimum max potency for top lead consideration
MIN_FREQUENCY_FOR_MASTER_REGULATOR = 15  # Frequency threshold for master regulator genes

# File Paths
GCTX_FILE = 'GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx'
GENE_METADATA = 'GSE92742_Broad_LINCS_gene_info.txt.gz'
SIG_METADATA = 'GSE92742_Broad_LINCS_sig_info.txt.gz'
PERT_INFO_FILE = 'GSE92742_Broad_LINCS_pert_info.txt.gz'

# Output File Names
COMPOUND_METADATA_CSV = 'lincs_compound_metadata.csv'
GENETIC_SIGNATURES_CSV = 'lincs_genetic_signatures.csv'
DATABASE_FILE = 'precision_pharmacology.db'
TOP_10_LEADS_SUMMARY = 'top_10_lead_summary.csv'
TOP_10_DETAILED_GENES = 'top_10_detailed_gene_hits.csv'
EXECUTIVE_LEAD_REPORT = 'final_executive_lead_report.csv'

# Database Configuration
DB_CHUNK_SIZE = 5000  # Number of rows to process at once for memory efficiency

# Web Scraping Configuration
PUBMED_BASE_URL = 'https://pubmed.ncbi.nlm.nih.gov/'
PUBMED_TIMEOUT = 10  # Timeout in seconds for web requests
PUBMED_RETRY_COUNT = 3  # Number of retries for failed requests
PUBMED_RETRY_DELAY = 2  # Delay between retries in seconds

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FILE = 'pipeline.log'

# Temporal Analysis (Phase 5)
TIME_POINTS = [6, 24]  # Time points (hours) for pharmacodynamics analysis

# Data Quality Checks
MIN_NON_NULL_THRESHOLD = 0.90  # Minimum percentage of non-null values required
MAX_DUPLICATE_THRESHOLD = 0.05  # Maximum percentage of duplicates tolerated
