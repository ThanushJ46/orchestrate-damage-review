import argparse
import os
import sys
import pandas as pd
import logging

# Ensure project root is in sys.path when running directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.utils import setup_logging, PipelineConfig
from src.data_loader import DataLoader
from src.claim_parser import ClaimParser
from src.image_analyzer import ImageAnalyzer
from src.ontology_mapper import OntologyMapper
from src.evidence_engine import EvidenceEngine
from src.risk_engine import RiskEngine
from src.decision_engine import DecisionEngine
from src.evaluation import Evaluation

logger = logging.getLogger("pipeline")

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Modal Evidence Review Pipeline")
    parser.add_argument("--input", default="data/claims.csv", help="Path to input claims CSV")
    parser.add_argument("--output", default="data/output.csv", help="Path to output CSV")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation against sample_claims.csv")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # 1. Setup logging and load config
    setup_logging()
    logger.info("Initializing Multi-Modal Evidence Review Pipeline")
    config = PipelineConfig()
    
    # 2. Ingest datasets
    loader = DataLoader()
    claims_df = pd.read_csv(args.input)
    user_history_df = loader.load_user_history()
    requirements_df = loader.load_evidence_requirements()
    
    # 3. Instantiate core components
    claim_parser = ClaimParser(config)
    image_analyzer = ImageAnalyzer(config)
    evidence_engine = EvidenceEngine(requirements_df)
    risk_engine = RiskEngine(user_history_df)
    decision_engine = DecisionEngine()
    
    # 4. Perform startup connectivity check
    logger.info("Performing Gemini API startup check...")
    connectivity_ok = claim_parser.caller.check_api_connectivity()
    if connectivity_ok:
        logger.info("Gemini API connection established successfully. Running in ONLINE mode.")
    else:
        logger.warning("Gemini API connection could not be verified. Operating in OFFLINE/MOCK mode.")
        
    results = []
    
    logger.info(f"Starting processing of {len(claims_df)} claims")
    
    for idx, row in claims_df.iterrows():
        user_id = row.get("user_id")
        image_paths_raw = str(row.get("image_paths")) if pd.notna(row.get("image_paths")) else ""
        user_claim = str(row.get("user_claim")) if pd.notna(row.get("user_claim")) else ""
        claim_object = str(row.get("claim_object")) if pd.notna(row.get("claim_object")) else ""
        
        logger.info(f"Processing claim {idx + 1}/{len(claims_df)} for user {user_id}")
        
        # Step 3.1: Parse the conversational claim
        raw_claim = claim_parser.parse_claim(user_claim, claim_object)
        std_claim = OntologyMapper.standardize_claim(raw_claim)
        
        # Step 3.2: Analyze visual evidence
        image_paths = [p.strip() for p in image_paths_raw.split(";") if p.strip()]
        std_analyses = []
        for path in image_paths:
            raw_analysis = image_analyzer.analyze_image(path)
            std_analysis = OntologyMapper.standardize_image(raw_analysis, std_claim["object_type"])
            std_analyses.append(std_analysis)
            
        # Step 3.3: Run Evidence evaluation
        evidence_res = evidence_engine.evaluate(std_claim, std_analyses)
        
        # Step 3.4: Evaluate risks
        risk_res = risk_engine.evaluate(user_id, std_claim, std_analyses, evidence_res)
        
        # Step 3.5: Synthesize decision
        decision_res = decision_engine.decide(std_claim, evidence_res, risk_res)
        
        # Step 3.6: Compile final row
        out_row = {
            "user_id": user_id,
            "image_paths": image_paths_raw,
            "user_claim": user_claim,
            "claim_object": claim_object,
            "evidence_standard_met": evidence_res["evidence_standard_met"],
            "evidence_standard_met_reason": evidence_res["evidence_standard_met_reason"],
            "risk_flags": risk_res["risk_flags"],
            "issue_type": std_claim["issue_type"],
            "object_part": std_claim["object_part"],
            "claim_status": decision_res["claim_status"],
            "claim_status_justification": decision_res["claim_status_justification"],
            "supporting_image_ids": evidence_res["supporting_image_ids"],
            "valid_image": evidence_res["valid_image"],
            "severity": decision_res["severity"]
        }
        
        results.append(out_row)
        
    # 4. Save outputs
    out_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    out_df.to_csv(args.output, index=False)
    logger.info(f"Processing complete. Saved outputs to {args.output}")
    
    # 5. Run Evaluation if flag is set
    if args.evaluate:
        logger.info("Running evaluation against sample claims...")
        evaluator = Evaluation(output_path=args.output)
        report = evaluator.evaluate_results()
        print("\n=== EVALUATION REPORT ===")
        try:
            print(report)
        except UnicodeEncodeError:
            print(report.encode("ascii", errors="replace").decode("ascii"))
        print("=========================")

if __name__ == "__main__":
    main()
