-- ==============================================================================
-- PROJECT: Precision Pharmacology Pipeline
-- DATABASE SCHEMA: 
-- 1. compound_metadata (pert_iname, moa, target, canonical_smiles, pubchem_cid)
-- 2. genetic_signatures (pert_iname, sig_id, pr_gene_symbol, z_score, is_significant)
-- ==============================================================================

-- QUESTION 1: Reversal of Disease Signatures
-- Goal: Find drugs that UP-REGULATE both DDIT4 and PSME1 (to treat a deficiency).
SELECT m.pert_iname, AVG(s.z_score) as avg_impact
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
WHERE s.pr_gene_symbol IN ('DDIT4', 'PSME1')
AND s.z_score > 2.0
GROUP BY m.pert_iname
HAVING COUNT(DISTINCT s.pr_gene_symbol) = 2
ORDER BY avg_impact DESC
LIMIT 10;

-- QUESTION 2: Mechanism of Action (MoA) Discovery
-- Goal: Find compounds that mimic the genetic fingerprint of 'bortezomib'
SELECT m.pert_iname, m.moa, COUNT(*) as matching_gene_count
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
WHERE s.pr_gene_symbol IN (
    SELECT pr_gene_symbol FROM genetic_signatures 
    WHERE pert_iname = 'bortezomib' AND z_score > 3.0
)
AND s.z_score > 3.0
AND m.pert_iname != 'bortezomib'
GROUP BY m.pert_iname, m.moa
ORDER BY matching_gene_count DESC
LIMIT 10;

-- QUESTION 3: Safety and Toxicity Prediction
-- Goal: Identify compounds with extreme transcriptomic volatility (|Z| > 4.0)
SELECT m.pert_iname, COUNT(*) as extreme_hit_count
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
WHERE abs(s.z_score) > 4.0
GROUP BY m.pert_iname
ORDER BY extreme_hit_count DESC
LIMIT 20;

-- QUESTION 4: Drug Potency Benchmarking
-- Goal: Top 10 compounds exhibiting maximum biological potency
SELECT m.pert_iname, m.moa, MAX(abs(s.z_score)) as max_potency
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
GROUP BY m.pert_iname, m.moa
ORDER BY max_potency DESC
LIMIT 10;

-- QUESTION 5: Identifying "Master Regulator" Genes
-- Goal: Which genes are the most responsive to chemical perturbation?
SELECT s.pr_gene_symbol, COUNT(*) as frequency
FROM genetic_signatures s
WHERE abs(s.z_score) > 2.0
GROUP BY s.pr_gene_symbol
ORDER BY frequency DESC
LIMIT 15;

-- QUESTION 6: Repurposing Efficiency
-- Goal: Find highly active known/FDA-approved drugs (filtering out 'BRD-' codes)
SELECT m.pert_iname, m.moa, COUNT(DISTINCT s.pr_gene_symbol) as genes_regulated
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
WHERE m.pert_iname NOT LIKE 'BRD-%' 
AND abs(s.z_score) > 3.0
GROUP BY m.pert_iname, m.moa
ORDER BY genes_regulated DESC
LIMIT 10;

-- QUESTION 7: Precision vs. Power (Data prep for Scatter Plot)
-- Goal: Compare maximum potency vs. number of affected genes for all drugs
SELECT m.pert_iname, 
       MAX(abs(s.z_score)) as max_potency, 
       COUNT(DISTINCT s.pr_gene_symbol) as affected_genes
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
GROUP BY m.pert_iname;

-- QUESTION 8: Therapeutic Class Validation (Internal QC)
-- Goal: Validate that known Proteasome Inhibitors hit expected gene markers
SELECT m.pert_iname, m.moa, s.pr_gene_symbol, AVG(s.z_score) as avg_z
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
WHERE s.pr_gene_symbol IN ('DDIT4', 'HSPA5')
GROUP BY m.pert_iname, m.moa, s.pr_gene_symbol
HAVING avg_z > 4.0
ORDER BY m.pert_iname;

-- QUESTION 9: Executive Summary of Top 10 Precision Leads
-- Goal: Identify top 10 surgical candidates (high potency, low off-target)
SELECT m.pert_iname, 
       m.moa,
       m.canonical_smiles,
       m.pubchem_cid,
       MAX(abs(s.z_score)) as max_potency, 
       COUNT(DISTINCT s.pr_gene_symbol) as total_gene_hits
FROM compound_metadata m
JOIN genetic_signatures s 
    ON m.pert_iname = s.pert_iname
GROUP BY m.pert_iname, m.moa, m.canonical_smiles, m.pubchem_cid
HAVING total_gene_hits <= 50 AND max_potency >= 8.0
ORDER BY max_potency DESC
LIMIT 10;

-- QUESTION 10: Precision Lead Clinical Selection (Final Recommendation)
-- Goal: Dynamically isolate the exact Z-scores for our Top 10 Leads across the Top 7 genes they specifically affect.

WITH Top10Leads AS (
    -- Step 1: Dynamically find the Top 10 Precision Leads
    SELECT m.pert_iname
    FROM compound_metadata m
    JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
    GROUP BY m.pert_iname
    HAVING COUNT(DISTINCT s.pr_gene_symbol) <= 50 AND MAX(abs(s.z_score)) >= 8.0
    ORDER BY MAX(abs(s.z_score)) DESC
    LIMIT 10
),
Top7Genes AS (
    -- Step 2: Find the Top 7 genes most heavily affected by ONLY those 10 leads
    SELECT s.pr_gene_symbol
    FROM genetic_signatures s
    JOIN Top10Leads t ON s.pert_iname = t.pert_iname
    WHERE abs(s.z_score) >= 2.0
    GROUP BY s.pr_gene_symbol
    ORDER BY COUNT(*) DESC
    LIMIT 7
)
-- Step 3: Build the final interaction matrix
SELECT m.pert_iname, m.moa, s.pr_gene_symbol, s.z_score
FROM compound_metadata m
JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
JOIN Top10Leads t ON m.pert_iname = t.pert_iname
JOIN Top7Genes g ON s.pr_gene_symbol = g.pr_gene_symbol;