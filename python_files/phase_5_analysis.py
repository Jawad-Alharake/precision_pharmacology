"""
Phase 5: Temporal Pharmacodynamics & Clinical Profile Classification
Analyze temporal biomarker responses and classify clinical profiles using ML.
"""

from typing import Optional, Dict, Tuple
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import sqlite3
import config
from logger import setup_logger
from exceptions import TemporalAnalysisError

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger_temp = setup_logger(__name__)
    logger_temp.warning("scikit-learn not available. Install it for ML features.")


logger = setup_logger(__name__)


def extract_temporal_features(conn: sqlite3.Connection, 
                             time_points: Optional[list] = None) -> pd.DataFrame:
    """
    Extract temporal biomarker response features.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        time_points (list): Time points for analysis. Defaults to config.TIME_POINTS.
    
    Returns:
        pd.DataFrame: Temporal features.
        
    Raises:
        TemporalAnalysisError: If extraction fails.
    """
    if time_points is None:
        time_points = config.TIME_POINTS
    
    logger.info(f"Extracting temporal features for time points: {time_points}")
    
    try:
        query = '''
            SELECT 
                m.pert_iname,
                COUNT(DISTINCT s.pr_gene_symbol) as biomarker_count,
                AVG(ABS(s.z_score)) as avg_response,
                MAX(ABS(s.z_score)) as max_response,
                STDDEV(s.z_score) as response_variability
            FROM compound_metadata m
            JOIN genetic_signatures s ON m.pert_iname = s.pert_iname
            WHERE s.is_significant = 1
            GROUP BY m.pert_iname
        '''
        
        features = pd.read_sql_query(query, conn)
        logger.info(f"Extracted features for {len(features)} compounds")
        return features
    
    except Exception as e:
        logger.error(f"Error extracting temporal features: {e}")
        raise TemporalAnalysisError(f"Feature extraction failed: {e}")


def classify_clinical_profiles(features: pd.DataFrame, 
                              use_ml: bool = True) -> pd.DataFrame:
    """
    Classify compounds into clinical profiles based on features.
    
    Args:
        features (pd.DataFrame): Input feature dataframe.
        use_ml (bool): Use ML model if True, else use rule-based classification.
    
    Returns:
        pd.DataFrame: Features with clinical profile classifications.
        
    Raises:
        TemporalAnalysisError: If classification fails.
    """
    logger.info(f"Classifying clinical profiles (ML={use_ml})...")
    
    if features is None or len(features) == 0:
        raise TemporalAnalysisError("Feature dataframe is empty")
    
    try:
        features = features.copy()
        
        if use_ml and SKLEARN_AVAILABLE:
            # ML-based classification
            features = _classify_with_ml(features)
        else:
            # Rule-based classification
            features = _classify_rule_based(features)
        
        logger.info(f"Classification complete. Profile distribution:")
        logger.info(features['clinical_profile'].value_counts().to_string())
        
        return features
    
    except Exception as e:
        logger.error(f"Error classifying clinical profiles: {e}")
        raise TemporalAnalysisError(f"Classification failed: {e}")


def _classify_rule_based(features: pd.DataFrame) -> pd.DataFrame:
    """Rule-based clinical profile classification."""
    features['clinical_profile'] = 'Unknown'
    
    # High potency, targeted (surgical)
    mask = (features['max_response'] >= config.MIN_POTENCY) & (features['biomarker_count'] <= config.MAX_AFFECTED_GENES)
    features.loc[mask, 'clinical_profile'] = 'Precision_Lead'
    
    # High potency, broad effects
    mask = (features['max_response'] >= config.MIN_POTENCY) & (features['biomarker_count'] > config.MAX_AFFECTED_GENES)
    features.loc[mask, 'clinical_profile'] = 'Broad_Spectrum'
    
    # Moderate potency
    mask = (features['max_response'] >= config.POTENCY_THRESHOLD) & (features['max_response'] < config.MIN_POTENCY)
    features.loc[mask, 'clinical_profile'] = 'Moderate_Impact'
    
    # Low potency
    mask = features['max_response'] < config.POTENCY_THRESHOLD
    features.loc[mask, 'clinical_profile'] = 'Low_Activity'
    
    return features


def _classify_with_ml(features: pd.DataFrame) -> pd.DataFrame:
    """ML-based clinical profile classification."""
    if not SKLEARN_AVAILABLE:
        logger.warning("scikit-learn not available, falling back to rule-based")
        return _classify_rule_based(features)
    
    try:
        # Define profiles based on heuristics
        profiles = _define_profiles(features)
        
        # Prepare features for ML
        X = features[['biomarker_count', 'avg_response', 'max_response', 'response_variability']].fillna(0)
        y = profiles
        
        # Train classifier
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        clf.fit(X_scaled, y)
        
        # Make predictions
        predictions = clf.predict(X_scaled)
        features['clinical_profile'] = predictions
        
        # Store model metrics
        accuracy = accuracy_score(y, predictions)
        logger.info(f"ML Model Accuracy: {accuracy:.2%}")
        
        return features
    
    except Exception as e:
        logger.warning(f"ML classification failed, using rule-based: {e}")
        return _classify_rule_based(features)


def _define_profiles(features: pd.DataFrame) -> np.ndarray:
    """Define target profiles for training."""
    profiles = np.array(['Unknown'] * len(features))
    
    mask = (features['max_response'] >= config.MIN_POTENCY) & (features['biomarker_count'] <= config.MAX_AFFECTED_GENES)
    profiles[mask] = 'Precision_Lead'
    
    mask = (features['max_response'] >= config.MIN_POTENCY) & (features['biomarker_count'] > config.MAX_AFFECTED_GENES)
    profiles[mask] = 'Broad_Spectrum'
    
    mask = (features['max_response'] >= config.POTENCY_THRESHOLD) & (features['max_response'] < config.MIN_POTENCY)
    profiles[mask] = 'Moderate_Impact'
    
    mask = features['max_response'] < config.POTENCY_THRESHOLD
    profiles[mask] = 'Low_Activity'
    
    return profiles


def evaluate_profile_model(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    """
    Evaluate clinical profile classification model.
    
    Args:
        y_true (np.ndarray): True labels.
        y_pred (np.ndarray): Predicted labels.
    
    Returns:
        dict: Evaluation metrics.
    """
    if not SKLEARN_AVAILABLE:
        return {}
    
    try:
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_weighted': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall_weighted': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            'f1_weighted': f1_score(y_true, y_pred, average='weighted', zero_division=0)
        }
        
        logger.info("Model Evaluation Metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error evaluating model: {e}")
        return {}


def generate_temporal_report(profiles: pd.DataFrame, 
                            output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Generate temporal analysis and clinical profile report.
    
    Args:
        profiles (pd.DataFrame): Classified profiles.
        output_path (str): Output file path.
    
    Returns:
        pd.DataFrame: Enhanced profiles with report metrics.
        
    Raises:
        TemporalAnalysisError: If report generation fails.
    """
    logger.info("Generating temporal analysis report...")
    
    try:
        if output_path is None:
            output_path = f"temporal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Add report metrics
        profiles['report_generated_at'] = datetime.now().isoformat()
        profiles['temporal_index'] = np.arange(len(profiles))
        
        # Save report
        profiles.to_csv(output_path, index=False)
        logger.info(f"✓ Report saved to {output_path}")
        
        return profiles
    
    except Exception as e:
        logger.error(f"Error generating temporal report: {e}")
        raise TemporalAnalysisError(f"Report generation failed: {e}")


def predict_clinical_response(conn: sqlite3.Connection, 
                             compound_name: str,
                             use_ml: bool = True) -> Dict:
    """
    Predict clinical response profile for a specific compound.
    
    Args:
        conn (sqlite3.Connection): Database connection.
        compound_name (str): Compound identifier.
        use_ml (bool): Use ML model.
    
    Returns:
        dict: Prediction and confidence.
        
    Raises:
        TemporalAnalysisError: If prediction fails.
    """
    logger.info(f"Predicting clinical response for: {compound_name}")
    
    try:
        # Get compound features
        query = '''
            SELECT 
                COUNT(DISTINCT s.pr_gene_symbol) as biomarker_count,
                AVG(ABS(s.z_score)) as avg_response,
                MAX(ABS(s.z_score)) as max_response,
                STDDEV(s.z_score) as response_variability
            FROM genetic_signatures s
            WHERE s.pert_iname = ?
        '''
        
        cursor = conn.cursor()
        cursor.execute(query, (compound_name,))
        result = cursor.fetchone()
        
        if not result or result[0] is None:
            raise TemporalAnalysisError(f"Compound '{compound_name}' not found")
        
        # Create feature vector
        features = pd.DataFrame([{
            'biomarker_count': result[0] or 0,
            'avg_response': result[1] or 0.0,
            'max_response': result[2] or 0.0,
            'response_variability': result[3] or 0.0
        }])
        
        # Predict profile
        profile_df = classify_clinical_profiles(features, use_ml)
        prediction = profile_df.iloc[0]['clinical_profile']
        
        logger.info(f"Prediction: {prediction}")
        
        return {
            'compound': compound_name,
            'predicted_profile': prediction,
            'features': features.iloc[0].to_dict()
        }
    
    except Exception as e:
        logger.error(f"Error predicting clinical response: {e}")
        raise TemporalAnalysisError(f"Prediction failed: {e}")
