import logging

logger = logging.getLogger("pipeline")

class EvidenceEngine:
    def __init__(self, requirements_df=None):
        self.requirements = requirements_df

    def evaluate(self, claim: dict, analyses: list) -> dict:
        """
        Evaluate if the visual evidence (analyses) satisfies the claim and the rules.
        """
        claim_object = claim.get("object_type", "unknown")
        claim_part = claim.get("object_part", "unknown")
        claim_issue = claim.get("issue_type", "unknown")

        supporting_image_ids = []
        part_visible = False
        object_match = False
        valid_image = True
        reasons = []

        # Analyze each image
        for analysis in analyses:
            img_id = analysis.get("image_id", "none")
            visible_obj = analysis.get("visible_object", "unknown")
            visible_parts = analysis.get("visible_parts", [])
            visible_damage = analysis.get("visible_damage", "unknown")
            quality_flags = analysis.get("quality_flags", [])

            # Check if primary object type matches
            if visible_obj == claim_object:
                object_match = True
            
            # Check if claimed part is visible in this image
            if claim_part in visible_parts or (claim_part == "unknown" and len(visible_parts) > 0):
                part_visible = True
                supporting_image_ids.append(img_id)
                
            # Check image validity
            # If the image is flagged as non-original (fake/screen photo), it is invalid
            if "non_original_image" in quality_flags or "cropped_or_obstructed" in quality_flags:
                valid_image = False

        evidence_standard_met = False
        reason = ""

        if not analyses:
            evidence_standard_met = False
            reason = "No images were submitted with the claim."
            valid_image = False
        elif not object_match:
            evidence_standard_met = False
            reason = f"The submitted images show a different object rather than the claimed {claim_object}."
        elif not part_visible:
            evidence_standard_met = False
            reason = f"The image does not show the claimed {claim_part}, so the condition cannot be verified."
        else:
            # The part is visible. Check if we have quality flags on the supporting images that block validation
            blocking_flags = []
            for analysis in analyses:
                if analysis.get("image_id") in supporting_image_ids:
                    q_flags = analysis.get("quality_flags", [])
                    for f in q_flags:
                        if f in ["blurry_image", "wrong_angle", "cropped_or_obstructed"] and f != "none":
                            blocking_flags.append(f)

            if blocking_flags:
                evidence_standard_met = False
                reason = f"The claimed {claim_part} is visible but the image quality or angle is insufficient ({', '.join(blocking_flags)})."
            else:
                evidence_standard_met = True
                # Match reason text based on whether the damage matches or not
                damage_matched = False
                for analysis in analyses:
                    if analysis.get("image_id") in supporting_image_ids:
                        if analysis.get("visible_damage") == claim_issue:
                            damage_matched = True
                
                if damage_matched:
                    reason = f"The {claim_part} is visible and the claimed {claim_issue} can be verified from the submitted images."
                else:
                    reason = f"The {claim_part} is visible and sufficient to evaluate, but the visible damage does not match the claimed {claim_issue}."

        # If no supporting images found, return "none"
        if not supporting_image_ids:
            supporting_image_str = "none"
        else:
            supporting_image_str = ";".join(supporting_image_ids)

        return {
            "evidence_standard_met": "true" if evidence_standard_met else "false",
            "evidence_standard_met_reason": reason,
            "supporting_image_ids": supporting_image_str,
            "valid_image": "true" if valid_image else "false"
        }
