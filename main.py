"""
ETL Pipeline Orchestrator

This script orchestrates the complete ETL process:
- Extract: Read source CSV files
- Transform: Normalize and validate data
- Load: Insert to PostgreSQL staging and DW schemas
- Reconcile: Validate staging vs. source CSVs (GATE before DW load)
- Verify: Generate quality reports

Usage:
    python main.py --phase all
    python main.py --phase transform
    python main.py --phase load-staging
    python main.py --phase reconcile
    python main.py --phase load-dw
    python main.py --phase all --force-dw-load
"""

import argparse
import sys
import logging
from pathlib import Path

from config.db_config import DB_CONFIG, LOG_LEVEL, REPORTS_FOLDER
from etl.extractor import extract_all_csvs
from etl.transformer import transform_to_canonical
from etl.loader_python import load_to_staging, create_dw_schema, load_to_dw
from etl.aggregator import setup_aggregation_schema, refresh_data_mart, validate_aggregations
from etl.validator import generate_quality_report
from etl.reconciler import reconcile_staging_to_source, ReconciliationError
from utils.logger import get_logger
from utils.helpers import ensure_directory

# Get logger
logger = get_logger("main")

# Global state for passing data between phases
_EXTRACTED_DATA = None
_TRANSFORMED_DATA = None


def setup_environment():
    """Set up environment (directories, etc.)"""
    ensure_directory(REPORTS_FOLDER)
    logger.info("Environment setup complete")


def validate_config():
    """Validate configuration"""
    logger.info("Validating configuration...")
    
    if not DB_CONFIG.get('user'):
        logger.error("Database user not configured")
        return False
    
    if not DB_CONFIG.get('password'):
        logger.error("Database password not configured in .env")
        return False
    
    if not DB_CONFIG.get('host'):
        logger.error("Database host not configured")
        return False
    
    logger.info(f"[OK] Configuration valid: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    return True


def phase_extract(args):
    """Execute extraction phase"""
    global _EXTRACTED_DATA
    
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 1: EXTRACTION")
    logger.info("=" * 100)
    
    try:
        _EXTRACTED_DATA = extract_all_csvs()
        logger.info(f"[OK] Extracted {len(_EXTRACTED_DATA)} CSV files")
        return True
    except Exception as e:
        logger.error(f"[FAIL] Extraction failed: {str(e)}")
        return False


def phase_transform(args):
    """Execute transformation phase"""
    global _EXTRACTED_DATA, _TRANSFORMED_DATA
    
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 2: TRANSFORMATION")
    logger.info("=" * 100)
    
    try:
        # If extract phase not run, load from extraction
        if _EXTRACTED_DATA is None:
            logger.info("Extracted data not in memory, re-extracting...")
            _EXTRACTED_DATA = extract_all_csvs()
        
        _TRANSFORMED_DATA = transform_to_canonical(
            _EXTRACTED_DATA, 
            skip_validation=args.skip_validation
        )
        logger.info(f"[OK] Transformed to {len(_TRANSFORMED_DATA)} rows")
        return True
    except Exception as e:
        logger.error(f"[FAIL] Transformation failed: {str(e)}")
        return False


def phase_load_staging(args):
    """Execute staging load phase"""
    global _TRANSFORMED_DATA
    
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 4: LOAD TO STAGING")
    logger.info("=" * 100)
    
    try:
        # If transform phase not run, run it
        if _TRANSFORMED_DATA is None:
            logger.info("Transformed data not in memory, running transformation...")
            if not phase_transform(args):
                return False
        
        success = load_to_staging(_TRANSFORMED_DATA)
        
        if success:
            logger.info("[OK] Staging load complete")
        else:
            logger.error("[FAIL] Staging load failed")
        
        return success
    except Exception as e:
        logger.error(f"[FAIL] Staging load error: {str(e)}")
        return False


def phase_reconcile(args):
    """Execute reconciliation gate phase"""
    global _TRANSFORMED_DATA
    
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 3: RECONCILIATION VALIDATION GATE")
    logger.info("=" * 100)
    logger.info("This gate validates that transformed data matches source CSVs")
    logger.info("DW load will be BLOCKED if reconciliation fails")
    logger.info("")
    
    try:
        # Ensure we have transformed data to reconcile
        if _TRANSFORMED_DATA is None:
            logger.info("Transformed data not in memory, re-extracting and transforming...")
            if not phase_extract(args) or not phase_transform(args):
                return False
        
        result = reconcile_staging_to_source(
            _TRANSFORMED_DATA,
            output_file='reports/reconciliation_report.txt'
        )
        logger.info("[OK] Reconciliation PASSED - DW load approved")
        return True
    except ReconciliationError as e:
        logger.error(f"[FAIL] Reconciliation FAILED: {str(e)}")
        
        if args.force_dw_load:
            logger.warning("[WARNING] Forcing DW load despite reconciliation failure (--force-dw-load flag)")
            return True  # Return True to allow proceeding
        else:
            logger.error("DW load BLOCKED. To override, use: python main.py --force-dw-load")
            return False
    except Exception as e:
        logger.error(f"[FAIL] Reconciliation error: {str(e)}")
        return False


def phase_create_dw(args):
    """Execute DW schema creation phase"""
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 5: CREATE DATA WAREHOUSE SCHEMA")
    logger.info("=" * 100)
    
    try:
        success = create_dw_schema()
        
        if success:
            logger.info("[OK] DW schema creation complete")
        else:
            logger.error("[FAIL] DW schema creation failed")
        
        return success
    except Exception as e:
        logger.error(f"[FAIL] DW schema creation error: {str(e)}")
        return False


def phase_load_dw(args):
    """Execute DW fact table load phase"""
    global _TRANSFORMED_DATA
    
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 6: LOAD DATA WAREHOUSE FACT TABLE")
    logger.info("=" * 100)
    
    try:
        # If transform phase not run, re-transform
        if _TRANSFORMED_DATA is None:
            logger.info("Transformed data not in memory, re-extracting and transforming...")
            _EXTRACTED_DATA = extract_all_csvs()
            _TRANSFORMED_DATA = transform_to_canonical(_EXTRACTED_DATA, skip_validation=args.skip_validation)
        
        # Load to fact table
        success = load_to_dw(_TRANSFORMED_DATA)
        
        if success:
            logger.info("[OK] DW fact table load complete")
        else:
            logger.error("[FAIL] DW fact table load failed")
        
        return success
    except Exception as e:
        logger.error(f"[FAIL] DW load error: {str(e)}")
        return False


def phase_aggregation(args):
    """Execute data mart aggregation phase"""
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 7: DATA MART AGGREGATION")
    logger.info("=" * 100)
    
    try:
        # Setup aggregation schema and tables
        setup_aggregation_schema()
        
        # Refresh aggregation tables
        rows1, rows2 = refresh_data_mart()
        
        # Validate aggregations
        validate_aggregations()
        
        logger.info("[OK] Data mart aggregation complete")
        return True
    except Exception as e:
        logger.error(f"[FAIL] Data mart aggregation error: {str(e)}")
        return False


def phase_validate(args):
    """Execute validation and reporting phase"""
    logger.info("")
    logger.info("=" * 100)
    logger.info("PHASE 8: VALIDATION & REPORTING")
    logger.info("=" * 100)
    
    try:
        report_path = generate_quality_report(
            DB_CONFIG,
            output_file='reports/validation_report.txt'
        )
        
        if report_path:
            logger.info(f"[OK] Quality report generated: {report_path}")
            return True
        else:
            logger.error("[FAIL] Failed to generate quality report")
            return False
    except Exception as e:
        logger.error(f"[FAIL] Validation error: {str(e)}")
        return False


def run_all_phases(args):
    """Run all ETL phases in sequence"""
    logger.info("Starting full ETL pipeline (--phase all)")
    logger.info("=" * 100)
    
    phases = [
        ("Extract", phase_extract),
        ("Transform", phase_transform),
        ("Reconcile", phase_reconcile),
        ("Load Staging", phase_load_staging),
        ("Create DW", phase_create_dw),
        ("Load DW", phase_load_dw),
        ("Aggregation", phase_aggregation),
        ("Validate", phase_validate),
    ]
    
    results = {}
    
    for phase_name, phase_func in phases:
        try:
            success = phase_func(args)
            results[phase_name] = success
            
            if not success:
                logger.error(f"[FAIL] {phase_name} phase failed")
                logger.error("Stopping pipeline")
                break
            else:
                logger.info(f"[OK] {phase_name} phase complete")
        except Exception as e:
            logger.error(f"[FAIL] {phase_name} phase error: {str(e)}")
            results[phase_name] = False
            break
    
    # Summary
    logger.info("")
    logger.info("=" * 100)
    logger.info("ETL PIPELINE SUMMARY")
    logger.info("=" * 100)
    
    for phase_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        logger.info(f"{status}: {phase_name}")
    
    all_passed = all(results.values())
    logger.info("")
    
    if all_passed:
        logger.info("[OK] ETL PIPELINE COMPLETE - ALL PHASES SUCCESSFUL")
        logger.info("Data warehouse is ready for analysis")
    else:
        logger.info("[FAIL] ETL PIPELINE INCOMPLETE - SEE ERRORS ABOVE")
    
    logger.info("=" * 100)
    
    return all_passed


def main():
    """Main entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="ETL Pipeline for Indonesian Statistics Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full ETL pipeline with reconciliation gate
  python main.py --phase all
  
  # Run individual phases
  python main.py --phase extract
  python main.py --phase transform
  python main.py --phase load-staging
  python main.py --phase reconcile
  python main.py --phase load-dw
  
  # Force DW load despite reconciliation failure
  python main.py --phase all --force-dw-load
  
  # Skip validation for quick test
  python main.py --phase transform --skip-validation
        """
    )
    
    parser.add_argument(
        "--phase",
        choices=[
            "extract", "transform", "load-staging", "reconcile", 
            "create-dw", "load-dw", "aggregation", "validate", "all"
        ],
        default="all",
        help="Which ETL phase to run (default: all)"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip data quality validation checks"
    )
    
    parser.add_argument(
        "--force-dw-load",
        action="store_true",
        help="Force DW load even if reconciliation fails (use with caution)"
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_environment()
    
    logger.info("")
    logger.info("=" * 100)
    logger.info("ETL PIPELINE FOR INDONESIAN STATISTICS DATA".center(100))
    logger.info("=" * 100)
    logger.info("")
    
    # Validate config
    if not validate_config():
        logger.error("Configuration validation failed")
        return 1
    
    # Route to appropriate phase
    try:
        if args.phase == "all":
            success = run_all_phases(args)
        elif args.phase == "extract":
            success = phase_extract(args)
        elif args.phase == "transform":
            success = phase_transform(args)
        elif args.phase == "load-staging":
            success = phase_load_staging(args)
        elif args.phase == "reconcile":
            success = phase_reconcile(args)
        elif args.phase == "create-dw":
            success = phase_create_dw(args)
        elif args.phase == "load-dw":
            success = phase_load_dw(args)
        elif args.phase == "aggregation":
            success = phase_aggregation(args)
        elif args.phase == "validate":
            success = phase_validate(args)
        else:
            logger.error(f"Unknown phase: {args.phase}")
            return 1
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        logger.warning("\n[FAIL] Pipeline interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"[FAIL] Unexpected error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
