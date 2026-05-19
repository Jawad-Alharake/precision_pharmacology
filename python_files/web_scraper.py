"""
Phase 4: Literature Footprint & Risk Assessment
Web scraper for PubMed to validate novelty and IP status of discovered compounds.
"""

from typing import Dict, List, Optional
import requests
import logging
import time
from urllib.parse import quote
from bs4 import BeautifulSoup
import pandas as pd
import config
from logger import setup_logger
from exceptions import ScraperError


logger = setup_logger(__name__)


class PubMedScraper:
    """Scraper for PubMed literature data with retry logic and rate limiting."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None, 
                 retry_count: Optional[int] = None, retry_delay: Optional[int] = None):
        """
        Initialize PubMed scraper.
        
        Args:
            base_url (str): PubMed base URL. Defaults to config.PUBMED_BASE_URL.
            timeout (int): Request timeout in seconds. Defaults to config.PUBMED_TIMEOUT.
            retry_count (int): Number of retries. Defaults to config.PUBMED_RETRY_COUNT.
            retry_delay (int): Delay between retries. Defaults to config.PUBMED_RETRY_DELAY.
        """
        self.base_url = base_url or config.PUBMED_BASE_URL
        self.timeout = timeout or config.PUBMED_TIMEOUT
        self.retry_count = retry_count or config.PUBMED_RETRY_COUNT
        self.retry_delay = retry_delay or config.PUBMED_RETRY_DELAY
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Precision Pharmacology Pipeline)'})
        logger.info("PubMed scraper initialized")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def search_compound(self, compound_name: str, max_results: int = 10) -> Dict:
        """
        Search for a compound on PubMed.
        
        Args:
            compound_name (str): Name of compound to search.
            max_results (int): Maximum number of results to retrieve.
        
        Returns:
            dict: Publication data dictionary.
            
        Raises:
            ScraperError: If search fails after retries.
        """
        if not compound_name or not isinstance(compound_name, str):
            raise ScraperError("Compound name must be a non-empty string")
        
        logger.info(f"Searching PubMed for compound: {compound_name}")
        
        retry = 0
        
        while retry < self.retry_count:
            try:
                # URL encode compound name for safety
                encoded_compound = quote(compound_name)
                search_url = f"{self.base_url}?term={encoded_compound}&retmax={max_results}&rettype=json"
                
                response = self.session.get(search_url, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                if 'result' in data and 'uids' in data['result']:
                    publication_count = len(data['result']['uids'])
                    logger.info(f"Found {publication_count} publications for '{compound_name}'")
                    
                    results = {
                        'compound': compound_name,
                        'publication_count': publication_count,
                        'pmids': data['result']['uids'][:max_results],
                        'status': 'novel' if publication_count < 5 else 'established'
                    }
                else:
                    logger.warning(f"No results found for '{compound_name}'")
                    results = {
                        'compound': compound_name,
                        'publication_count': 0,
                        'pmids': [],
                        'status': 'novel'
                    }
                
                return results
            
            except requests.exceptions.RequestException as e:
                retry += 1
                logger.warning(f"Request failed (attempt {retry}/{self.retry_count}): {e}")
                
                if retry < self.retry_count:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Max retries exceeded for '{compound_name}'")
                    results = {
                        'compound': compound_name,
                        'publication_count': -1,
                        'pmids': [],
                        'status': 'error'
                    }
                    return results
    
    def get_publication_details(self, pmid: str) -> Dict:
        """
        Get detailed information about a publication.
        
        Args:
            pmid (str): PubMed ID.
        
        Returns:
            dict: Publication details.
            
        Raises:
            ScraperError: If validation fails.
        """
        if not pmid or not isinstance(pmid, str):
            raise ScraperError("PMID must be a non-empty string")
        
        logger.debug(f"Fetching details for PMID: {pmid}")
        
        try:
            url = f"{self.base_url}{quote(pmid)}/"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1', class_='heading-title')
            title = title_elem.text.strip() if title_elem else 'N/A'
            
            # Extract year
            year_elem = soup.find('span', class_='cit')
            year = 'N/A'
            if year_elem:
                year_text = year_elem.text.strip()
                # Extract year (typically 4 digits)
                import re
                match = re.search(r'\d{4}', year_text)
                if match:
                    year = match.group(0)
            
            return {
                'pmid': pmid,
                'title': title,
                'year': year
            }
        
        except Exception as e:
            logger.warning(f"Error fetching details for PMID {pmid}: {e}")
            return {
                'pmid': pmid,
                'title': 'N/A',
                'year': 'N/A'
            }
    
    def batch_search(self, compound_list: List[str], max_results: int = 10) -> pd.DataFrame:
        """
        Search multiple compounds and aggregate results.
        
        Args:
            compound_list (list): List of compound names.
            max_results (int): Maximum results per compound.
        
        Returns:
            pd.DataFrame: Aggregated search results.
            
        Raises:
            ScraperError: If validation fails.
        """
        if not compound_list or not isinstance(compound_list, list):
            raise ScraperError("Compound list must be a non-empty list")
        
        logger.info(f"Starting batch search for {len(compound_list)} compounds...")
        
        results = []
        
        for i, compound in enumerate(compound_list):
            try:
                logger.info(f"Processing compound {i+1}/{len(compound_list)}: {compound}")
                
                search_result = self.search_compound(compound, max_results)
                results.append(search_result)
                
                # Rate limiting - be respectful to PubMed
                time.sleep(0.5)
            
            except Exception as e:
                logger.warning(f"Failed to search compound '{compound}': {e}")
                results.append({
                    'compound': compound,
                    'publication_count': -1,
                    'pmids': [],
                    'status': 'error'
                })
        
        results_df = pd.DataFrame(results)
        logger.info(f"✓ Batch search completed. Results for {len(results_df)} compounds")
        
        return results_df
    
    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            logger.info("PubMed scraper session closed")


def assess_novelty(publication_count: int, threshold: int = 5) -> str:
    """
    Assess whether a compound is novel based on publication count.
    
    Args:
        publication_count (int): Number of publications found.
        threshold (int): Threshold below which compound is considered novel.
    
    Returns:
        str: 'novel' or 'established'.
    """
    return 'novel' if publication_count < threshold else 'established'


def generate_novelty_report(search_results_df: pd.DataFrame, 
                           output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Generate a comprehensive novelty and risk assessment report.
    
    Args:
        search_results_df (pd.DataFrame): Results from batch search.
        output_path (str): Path to save report. Defaults to config value.
    
    Returns:
        pd.DataFrame: Enhanced results with novelty assessment.
        
    Raises:
        ScraperError: If report generation fails.
    """
    if output_path is None:
        output_path = config.EXECUTIVE_LEAD_REPORT
    
    logger.info("Generating novelty and risk assessment report...")
    
    try:
        search_results_df = search_results_df.copy()
        
        # Add assessment columns
        search_results_df['novelty_status'] = search_results_df['publication_count'].apply(assess_novelty)
        search_results_df['risk_level'] = search_results_df['publication_count'].apply(
            lambda x: 'LOW' if x > 50 else ('MEDIUM' if x > 10 else 'HIGH')
        )
        
        # Save report
        search_results_df.to_csv(output_path, index=False)
        logger.info(f"✓ Report saved to {output_path}")
        
        # Log summary
        novel_count = (search_results_df['novelty_status'] == 'novel').sum()
        established_count = (search_results_df['novelty_status'] == 'established').sum()
        
        logger.info(f"\nNovelty Report Summary:")
        logger.info(f"  Novel compounds: {novel_count}")
        logger.info(f"  Established compounds: {established_count}")
        
        if len(search_results_df) > 0:
            valid_results = search_results_df[search_results_df['publication_count'] >= 0]
            if len(valid_results) > 0:
                avg_publications = valid_results['publication_count'].mean()
                logger.info(f"  Average publications per compound: {avg_publications:.1f}")
        
        return search_results_df
    
    except Exception as e:
        logger.error(f"Error generating novelty report: {e}")
        raise ScraperError(f"Report generation failed: {e}")
