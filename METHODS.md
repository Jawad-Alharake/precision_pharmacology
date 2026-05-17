# Methods & Statistical Approach

## Overview
The Precision Pharmacology pipeline applies rigorous statistical and computational methods to identify promising drug repurposing candidates from the LINCS L1000 dataset.

## 1. Z-Score Standardization & Filtering

### Rationale
Gene expression changes are standardized as **Modified Z-scores (MODZ)** to account for:
- Batch effects across different experiments
- Variation in baseline gene expression
- Technical noise in the measurement platform

### Filtering Thresholds
- **Z > 2.0 or Z < -2.0**: Significant gene perturbation (biological signal)
- **|Z| > 3.0**: High-confidence hits (robust effects)
- **|Z| > 4.0**: Extreme effects (potential toxicity warning)

### Interpretation
- **Z > 0**: Gene UPREGULATED by compound
- **Z < 0**: Gene DOWNREGULATED by compound
- **|Z| > 2**: Effect unlikely due to noise (p < 0.05)

## 2. Precision vs. Power Analysis

### Precision (Specificity)
- **Definition**: Number of distinct genes affected by a compound
- **Lower is better**: A "surgical" drug hits fewer off-target genes
- **Threshold**: Max 50 genes regulated (after filtering)

### Power (Potency)
- **Definition**: Maximum absolute Z-score magnitude
- **Higher is better**: Stronger biological effect on target
- **Threshold**: Max potency ≥ 8.0 for top candidates

### Selection Criteria
Top 10 "precision leads" = Compounds with:
- **High potency** (Max |Z| ≥ 8.0)
- **High specificity** (≤ 50 affected genes)
- This combination identifies "surgical" drugs with strong, targeted effects

## 3. Master Regulator Gene Identification

### Concept
Genes that respond to chemical perturbation in many experiments are likely "hubs" in cellular regulation.

### Method
- Count frequency of genes with |Z| ≥ 2.0 across all compounds
- Genes appearing in >15 experiments are "master regulators"
- These are ideal drug targets

## 4. Disease Signature Reversal

### Mechanism
For therapeutic intervention:
1. Disease state: Genes A, B, C are UPREGULATED (Z > 2)
2. Therapeutic goal: Find drug that DOWNREGULATES A, B, C (Z < -2)
3. This represents "reversal" of disease signature

### Example
- **Disease**: Apoptosis genes downregulated → Cell death insufficient
- **Solution**: Find drug that UPREGULATES apoptosis genes → Restore cell death in cancer

## 5. Mechanism of Action (MoA) Discovery

### Approach
- Known drugs have validated gene signatures
- Unknown compounds (BRD codes) can be matched to known drugs
- If genetic fingerprints overlap, unknown drug likely has same MoA

### Implementation
- Find top genes affected by reference drug (Z > 3.0)
- Search for other compounds affecting same genes
- Matching compounds share mechanism of action

## 6. Off-Target Safety Assessment

### Extreme Transcriptomic Volatility
Compounds causing |Z| > 4.0 in many genes may indicate:
- Promiscuous binding (poor selectivity)
- Cellular stress response
- Potential toxicity risk

### Risk Filtering
Eliminate compounds with:
- >30 genes showing |Z| > 4.0 (likely toxic)
- Hits in known death pathway genes

## 7. Temporal Pharmacodynamics (Phase 5)

### Rationale
Drug effects mature over time (6h vs. 24h):
- **6 hours**: Immediate/direct effects (on-target)
- **24 hours**: Secondary effects (on-target strengthening or off-target emergence)

### Analysis
- Compare potency and gene hit count at each time point
- Compounds maintaining specificity over time: Better candidates
- Compounds showing new hits at 24h: Potential delayed toxicity

## 8. Data Quality Metrics

### Checks at Each Phase
1. **Null values**: < 10% in key columns
2. **Duplicates**: < 5% of total rows
3. **Z-score distribution**: Normal-like (mean ≈ 0, SD ≈ 1)
4. **Orphaned records**: Foreign key integrity maintained
5. **Memory efficiency**: Processing in chunks for large datasets

### Validation Queries
```sql
-- Check for data integrity
SELECT COUNT(*) as orphaned_signatures 
FROM genetic_signatures 
WHERE pert_iname NOT IN (SELECT pert_iname FROM compound_metadata);
```

## 9. Statistical Significance

### Power Analysis
- 1M+ experiments provide high statistical power
- Each compound tested multiple times (replicates averaged)
- MODZ accounts for experimental variation

### Multiple Testing
- No explicit correction (exploratory analysis)
- Pre-filtering (Z > 2.0) reduces false discovery burden
- Further validated by literature search (Phase 4)

## 10. Clinical Translation Criteria

### Top Lead Characteristics
1. ✓ High potency (Max |Z| ≥ 8.0)
2. ✓ High specificity (≤ 50 affected genes)
3. ✓ Known drug history or MoA clarity
4. ✓ Limited extreme hits (|Z| > 4.0)
5. ✓ Disease signature reversal match
6. ✓ Stable effects over time (6h → 24h)
7. ✓ Supported by limited prior literature (novel angle)

---

**References**
- Lamb, J., et al. (2006). "The Connectivity Map: Using Gene-Expression Signatures to Connect Small Molecules, Genes, and Disease." Science, 313(5795), 1929-1935.
- Subramanian, A., et al. (2017). "A Next Generation Connectivity Map: L1000 Platform and the First 1,000,000 Profiles." Cell, 171(6), 1437-1452.
