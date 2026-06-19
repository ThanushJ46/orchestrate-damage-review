import logging

logger = logging.getLogger("pipeline")

class DecisionEngine:
    def __init__(self):
        pass

    def decide(self, claim: dict, evidence_result: dict, risk_result: dict) -> dict:
        """
        Synthesize claim context, evidence evaluation, and risk compilation into the final decision.
        """
        evidence_met = evidence_result.get("evidence_standard_met") == "true"
        evidence_reason = evidence_result.get("evidence_standard_met_reason", "")
        
        risk_flags_str = risk_result.get("risk_flags", "none")
        risk_flags = [f.strip() for f in risk_flags_str.split(";")]

        claim_part = claim.get("object_part", "unknown")
        claim_issue = claim.get("issue_type", "unknown")
        severity_hint = claim.get("severity_hint", "unknown")

        claim_status = "not_enough_information"
        justification = ""
        severity = "unknown"

        if not evidence_met:
            # If evidence standard is not met, we generally lack information
            claim_status = "not_enough_information"
            severity = "unknown"
            
            if "wrong_object" in risk_flags:
                justification = "The claim cannot be verified because the submitted images show a different object or vehicle."
            elif "wrong_angle" in risk_flags or "blurry_image" in risk_flags or "cropped_or_obstructed" in risk_flags:
                justification = f"The images do not satisfy the evidence standard due to quality issues: {evidence_reason}"
            else:
                justification = f"Sufficient visual evidence was not provided to verify the claim. {evidence_reason}"
        else:
            # Evidence standard is met (target part is visible and inspectable)
            if "claim_mismatch" in risk_flags or "wrong_object" in risk_flags:
                # If there's a mismatch (e.g. no damage visible, or different damage visible)
                if "damage_not_visible" in risk_flags:
                    claim_status = "contradicted"
                    severity = "none"
                    justification = f"The image clearly shows the claimed {claim_part}, but there is no visible damage, which contradicts the claim."
                else:
                    claim_status = "contradicted"
                    severity = severity_hint if severity_hint != "unknown" else "low"
                    justification = f"The visual evidence contradicts the claim: {evidence_reason}"
            else:
                # No mismatch and evidence standard met -> Claim is supported!
                claim_status = "supported"
                severity = severity_hint if severity_hint != "unknown" else "medium"
                justification = f"The claim is supported because the image clearly shows the expected {claim_part} with the claimed {claim_issue}."

        # Adjust severity based on status
        if claim_status == "contradicted" and severity == "unknown":
            severity = "low"
        elif claim_status == "not_enough_information":
            severity = "unknown"

        return {
            "claim_status": claim_status,
            "claim_status_justification": justification,
            "severity": severity
        }
