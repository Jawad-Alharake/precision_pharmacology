# Troubleshooting Guide

## Common Issues & Solutions

### 1. Data Download Issues

**Problem**: "File not found" error when running Phase 1
```
FileNotFoundError: GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx not found
```

**Solutions**:
- Verify file is downloaded from: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE92742
- Ensure file is extracted (if downloaded as archive):
  ```bash
  gunzip GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx.gz
  ```
- Check that all 4 files are present:
  - `GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx` (~20GB)
  - `GSE92742_Broad_LINCS_gene_info.txt.gz` (~200KB)
  - `GSE92742_Broad_LINCS_sig_info.txt.gz` (~11MB)
  - `GSE92742_Broad_LINCS_pert_info.txt.gz` (~5MB)

**Problem**: Download is very slow or times out
- NCBI servers can be slow; try downloading during off-peak hours
- Consider using `wget` or `curl` for better reliability:
  ```bash
  wget ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE92nnn/GSE92742/suppl/...
  ```

---

### 2. Memory Issues

**Problem**: "MemoryError" when loading GCTX file
```
MemoryError: Unable to allocate 8.5 GiB for an array
```

**Solutions**:
- The GCTX file is ~20GB; ensure you have at least 50GB free RAM
- Use chunked processing in Phase 1:
  ```python
  from python_files.data_extraction import parse_gctx_file
  # Module automatically handles chunking
  ```
- Close unnecessary applications to free up memory
- On limited-memory systems, consider processing on a cloud machine (AWS EC2, Google Colab)

**Problem**: Jupyter kernel crashes during Phase 2 database ingestion
- Reduce `config.DB_CHUNK_SIZE` to smaller value:
  ```python
  # In config.py
  DB_CHUNK_SIZE = 1000  # Instead of 5000
  ```

---

### 3. Database Issues

**Problem**: "database is locked" error
```
sqlite3.OperationalError: database is locked
```

**Solutions**:
- Close other notebooks/connections accessing `precision_pharmacology.db`
- Delete the database and rebuild:
  ```bash
  rm precision_pharmacology.db
  # Re-run Phase 2
  ```
- Increase timeout in database connection:
  ```python
  conn = sqlite3.connect('precision_pharmacology.db', timeout=30.0)
  ```

**Problem**: Duplicate key errors in Phase 2
```
sqlite3.IntegrityError: UNIQUE constraint failed: compound_metadata.pert_iname
```

**Solutions**:
- Drop and recreate the database:
  ```python
  from python_files.database import create_database, create_schema
  conn = create_database()
  create_schema(conn)
  ```
- Check for duplicate compounds in source data before ingestion

**Problem**: Queries returning no results (empty DataFrames)
- Verify database has data:
  ```sql
  SELECT COUNT(*) FROM compound_metadata;
  SELECT COUNT(*) FROM genetic_signatures;
  ```
- Check that Phase 1 and Phase 2 completed successfully
- Verify query thresholds in `config.py` aren't too strict

---

### 4. Import Errors

**Problem**: "ModuleNotFoundError: No module named 'gctx'"
```
ModuleNotFoundError: No module named 'gctx'
```

**Solutions**:
- Install required packages:
  ```bash
  pip install -r requirements.txt
  ```
- For GCTX support, install cmapPy:
  ```bash
  pip install cmapPy
  ```

**Problem**: "No module named 'beautifulsoup4'"
- Install missing dependency:
  ```bash
  pip install beautifulsoup4
  ```

---

### 5. Phase 4 Web Scraping Issues

**Problem**: PubMed scraper returns empty results
```
Found 0 publications for compound_name
```

**Solutions**:
- PubMed API is rate-limited; retry after 60 seconds
- Use full chemical names instead of abbreviations:
  - ✓ "aspirin"
  - ✗ "ASA"
- Some BRD compounds may not be in PubMed; this is expected
- Check `pipeline.log` for HTTP errors

**Problem**: "ConnectionError: Failed to establish connection"
- Network connectivity issue; check internet connection
- PubMed server may be down; retry later
- Scraper will automatically retry up to 3 times (configurable in `config.py`)

---

### 6. Results/Output Issues

**Problem**: "Permission denied" error when saving results
```
PermissionError: [Errno 13] Permission denied: 'top_10_lead_summary.csv'
```

**Solutions**:
- Ensure write permissions in current directory
- Use absolute path in config:
  ```python
  # In config.py
  TOP_10_LEADS_SUMMARY = '/home/user/results/top_10_lead_summary.csv'
  ```
- Create results directory if it doesn't exist:
  ```bash
  mkdir -p results
  ```

**Problem**: CSV files showing encoding errors
- Files are saved with UTF-8 encoding by default
- Open with proper encoding in Excel:
  - Excel → Data → From Text → Select UTF-8
- Or use Python:
  ```python
  import pandas as pd
  df = pd.read_csv('file.csv', encoding='utf-8')
  ```

---

### 7. Phase 5 (Temporal Analysis) Issues

**Problem**: "KeyError: 6 or 24" in Phase 5
```
KeyError: 'The column labels [6, 24] are not found'
```

**Solutions**:
- Verify that time point data is in your source files
- Check that original data includes both 6h and 24h timepoints
- Modify `config.py` if using different time points:
  ```python
  TIME_POINTS = [12, 48]  # Different time points
  ```

---

### 8. Performance Issues

**Problem**: Phase 1 is taking > 2 hours
- This is normal for 1M+ records on standard hardware
- Monitor progress in `pipeline.log`
- For faster processing, increase memory and chunk size (if you have the RAM)

**Problem**: SQL queries in Phase 3 are very slow
- Add indexes (should be automatic in Phase 2):
  ```sql
  CREATE INDEX idx_pert_iname ON genetic_signatures(pert_iname);
  CREATE INDEX idx_gene_symbol ON genetic_signatures(pr_gene_symbol);
  ```
- Analyze query plan:
  ```sql
  EXPLAIN QUERY PLAN SELECT ... ;
  ```

---

### 9. Reproducibility Issues

**Problem**: "Different results when re-running pipeline"
- Verify you're using the same `config.py` parameters
- Check that input data files haven't changed
- Ensure random seeds are set (if applicable)
- Review the timestamp in output files to check recency

**Problem**: "Results don't match previous run"
- Different Python/pandas versions might affect calculations
- Lock dependency versions in `requirements.txt`
- Document the environment:
  ```bash
  pip freeze > environment.txt
  python --version
  ```

---

### 10. Documentation & Logging

**Problem**: Can't find logs from previous runs
- Check `pipeline.log` in current directory
- Logs include:
  - Phase start/end times
  - Data shape changes
  - Filtering statistics
  - Errors and warnings
- Review logs with:
  ```bash
  tail -f pipeline.log  # Stream live logs
  grep ERROR pipeline.log  # Find all errors
  ```

---

## Getting More Help

1. **Check the logs**: 
   - First check `pipeline.log` for detailed error messages

2. **Review METHODS.md**:
   - Understand the statistical approach and thresholds

3. **Examine config.py**:
   - Verify parameters match your use case

4. **Test individual modules**:
   ```python
   from python_files.data_extraction import validate_data_quality
   report = validate_data_quality(my_dataframe)
   print(report)
   ```

5. **Debug in Jupyter**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   # Re-run problematic cell
   ```

---

## System Requirements

### Minimum
- 50GB free disk space
- 32GB RAM
- Python 3.8+

### Recommended
- 100GB free disk space
- 64GB RAM
- Python 3.10+
- SSD for database operations

---

## Contact & Reporting Bugs

For bugs, feature requests, or questions:
- Create an Issue in the GitHub repository
- Include error message, log output, and configuration used
- Specify Python version and system details
