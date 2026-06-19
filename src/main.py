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
        logger.info(f"[DEFENSIVE LOG] Raw Gemini ClaimParser Output: {raw_claim}")
        
        std_claim = OntologyMapper.standardize_claim(raw_claim)
        logger.info(f"[DEFENSIVE LOG] Ontology-Normalized Claim: {std_claim}")
        
        # Step 3.2: Analyze visual evidence
        image_paths = [p.strip() for p in image_paths_raw.split(";") if p.strip()]
        std_analyses = []
        for path in image_paths:
            import os
            raw_analysis = image_analyzer.analyze_image(
                path,
                claim_object=std_claim.get("object_type"),
                claim_part=std_claim.get("object_part"),
                claim_issue=std_claim.get("issue_type")
            )
            logger.info(f"[DEFENSIVE LOG] Raw Gemini ImageAnalyzer Output for {os.path.basename(path)}: {raw_analysis}")
            
            std_analysis = OntologyMapper.standardize_image(raw_analysis, std_claim["object_type"])
            logger.info(f"[DEFENSIVE LOG] Ontology-Normalized Image Analysis for {os.path.basename(path)}: {std_analysis}")
            std_analyses.append(std_analysis)
            
        # Step 3.3: Run Evidence evaluation
        logger.info(f"[DEFENSIVE LOG] Final EvidenceEngine Inputs - Claim: {std_claim}, Analyses: {std_analyses}")
        evidence_res = evidence_engine.evaluate(std_claim, std_analyses)
        
        # Step 3.4: Evaluate risks
        risk_res = risk_engine.evaluate(user_id, std_claim, std_analyses, evidence_res)
        
        # Step 3.5: Synthesize decision
        decision_res = decision_engine.decide(std_claim, evidence_res, risk_res)
        
        # Step 3.6: Compile final row
        out_part = std_claim["object_part"]
        out_issue = std_claim["issue_type"]
        
        if decision_res["claim_status"] == "contradicted":
            # If wrong object category mismatch
            if "wrong_object" in risk_res["risk_flags"]:
                has_diff_category = False
                for r_an in std_analyses:
                    vis_obj = r_an.get("visible_object")
                    if vis_obj != std_claim["object_type"] and vis_obj in ["car", "laptop", "package"]:
                        has_diff_category = True
                if has_diff_category:
                    out_part = "unknown"
                    out_issue = "unknown"
            # If claim mismatch (different damage/part visible)
            elif "claim_mismatch" in risk_res["risk_flags"] and "damage_not_visible" not in risk_res["risk_flags"]:
                visible_parts_list = []
                visible_damage_val = "unknown"
                for r_an in std_analyses:
                    if r_an.get("visible_damage") not in ["none", "unknown"]:
                        visible_damage_val = r_an.get("visible_damage")
                        visible_parts_list = r_an.get("visible_parts", [])
                
                if visible_damage_val != "unknown":
                    out_issue = visible_damage_val
                    out_part = visible_parts_list[0] if visible_parts_list else "unknown"
        
        out_row = {
            "user_id": user_id,
            "image_paths": image_paths_raw,
            "user_claim": user_claim,
            "claim_object": claim_object,
            "evidence_standard_met": evidence_res["evidence_standard_met"],
            "evidence_standard_met_reason": evidence_res["evidence_standard_met_reason"],
            "risk_flags": risk_res["risk_flags"],
            "issue_type": out_issue,
            "object_part": out_part,
            "claim_status": decision_res["claim_status"],
            "claim_status_justification": decision_res["claim_status_justification"],
            "supporting_image_ids": evidence_res["supporting_image_ids"],
            "valid_image": evidence_res["valid_image"],
            "severity": decision_res["severity"]
        }
        
        results.append(out_row)
        
    # 4. Save outputs
    out_df = pd.DataFrame(results)
    dirname = os.path.dirname(args.output)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
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
