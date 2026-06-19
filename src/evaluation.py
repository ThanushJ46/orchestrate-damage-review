import pandas as pd
import os
import logging

logger = logging.getLogger("pipeline")

class Evaluation:
    def __init__(self, output_path="data/output.csv", sample_path="data/sample_claims.csv"):
        self.output_path = output_path
        self.sample_path = sample_path

    def evaluate_results(self) -> str:
        if not os.path.exists(self.output_path):
            logger.error(f"Output file {self.output_path} not found for evaluation.")
            return "Error: Output file not found."
        if not os.path.exists(self.sample_path):
            logger.error(f"Sample claims file {self.sample_path} not found for evaluation.")
            return "Error: Sample claims file not found."

        out_df = pd.read_csv(self.output_path)
        sample_df = pd.read_csv(self.sample_path)

        # Merge on user_id and image_paths to align comparisons
        merged = pd.merge(
            sample_df,
            out_df,
            on=["user_id", "image_paths"],
            suffixes=("_true", "_pred"),
            how="inner"
        )

        if merged.empty:
            logger.warning("No matching claims found between output and sample claims for evaluation.")
            return "Error: No matching claims to evaluate."

        total = len(merged)
        metrics = {}

        # Columns to evaluate
        cols = [
            "evidence_standard_met",
            "claim_status",
            "valid_image",
            "severity",
            "issue_type",
            "object_part"
        ]

        for col in cols:
            col_true = f"{col}_true"
            col_pred = f"{col}_pred"
            
            if col_true in merged.columns and col_pred in merged.columns:
                # Calculate accuracy
                correct = (merged[col_true].astype(str).str.lower().str.strip() == 
                           merged[col_pred].astype(str).str.lower().str.strip()).sum()
                accuracy = correct / total
                metrics[col] = {
                    "accuracy": accuracy,
                    "correct": correct,
                    "total": total
                }

        # Build Markdown Report
        report = []
        report.append("# Pipeline Evaluation Report\n")
        report.append(f"**Total Evaluated Claims**: {total}\n")
        report.append("## Field Accuracy Metrics\n")
        report.append("| Field | Correct / Total | Accuracy |")
        report.append("| :--- | :--- | :--- |")
        for col, data in metrics.items():
            report.append(f"| `{col}` | {data['correct']} / {data['total']} | {data['accuracy']:.2%} |")

        report.append("\n## Detail Comparison & Failure Cases\n")
        report.append("| User ID | Field | Ground Truth | Prediction | Status |")
        report.append("| :--- | :--- | :--- | :--- | :--- |")

        failure_count = 0
        for _, row in merged.iterrows():
            user_id = row["user_id"]
            for col in cols:
                val_true = str(row[f"{col}_true"]).strip()
                val_pred = str(row[f"{col}_pred"]).strip()
                if val_true.lower() != val_pred.lower():
                    report.append(f"| {user_id} | `{col}` | `{val_true}` | `{val_pred}` | ❌ Mismatch |")
                    failure_count += 1
                else:
                    report.append(f"| {user_id} | `{col}` | `{val_true}` | `{val_pred}` | ✅ Match |")

        report_str = "\n".join(report)
        
        # Write report
        report_path = "evaluation_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_str)
            
        logger.info(f"Evaluation report written to {report_path}. Total failures: {failure_count}")
        return report_str
