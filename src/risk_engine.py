import logging

logger = logging.getLogger("pipeline")

class RiskEngine:
    def __init__(self, user_history_df=None):
        self.user_history = user_history_df

    def evaluate(self, user_id: str, claim: dict, analyses: list, evidence_result: dict) -> dict:
        """
        Compile risk flags based on user history and image analyzer quality flags.
        """
        flags = set()

        # 1. User History Risk
        user_flags = ""
        if self.user_history is not None and user_id in self.user_history.index:
            user_row = self.user_history.loc[user_id]
            user_flags = str(user_row.get("history_flags", ""))
            
            if "user_history_risk" in user_flags:
                flags.add("user_history_risk")
            if "manual_review_required" in user_flags:
                flags.add("manual_review_required")
        else:
            logger.warning(f"User history not found for user {user_id}")

        # 2. Quality Flags from Image Analyses
        damage_visible = False
        object_match = False
        wrong_object_detected = False
        
        claim_object = claim.get("object_type", "unknown")
        claim_issue = claim.get("issue_type", "unknown")

        for analysis in analyses:
            visible_obj = analysis.get("visible_object", "unknown")
            visible_damage = analysis.get("visible_damage", "unknown")
            q_flags = analysis.get("quality_flags", [])

            if visible_obj == claim_object:
                object_match = True
            elif visible_obj != "unknown" and visible_obj != "other":
                wrong_object_detected = True

            if visible_damage != "none" and visible_damage != "unknown":
                damage_visible = True

            for f in q_flags:
                if f != "none" and f != "":
                    flags.add(f)

        # 3. Add logical risk flags
        if wrong_object_detected or not object_match:
            flags.add("wrong_object")

        # Check for claim mismatch: if the visible damage does not match the claimed damage
        claim_mismatch = False
        if object_match and claim_issue != "none":
            # Check if there is any image showing the claimed issue
            matched_issue = False
            for analysis in analyses:
                if analysis.get("visible_damage") == claim_issue:
                    matched_issue = True
            
            if not matched_issue:
                claim_mismatch = True
        else:
            claim_mismatch = True

        if claim_mismatch:
            flags.add("claim_mismatch")

        # Damage not visible flag
        if not damage_visible or evidence_result.get("evidence_standard_met") == "false":
            # If the evidence standard says the part is not visible, then damage is not visible
            flags.add("damage_not_visible")

        # manual_review_required triggers
        if any(f in flags for f in ["blurry_image", "wrong_angle", "cropped_or_obstructed", "text_instruction_present", "non_original_image", "claim_mismatch", "wrong_object", "user_history_risk"]):
            flags.add("manual_review_required")

        # Clean flags list
        if "none" in flags:
            flags.remove("none")
        if "" in flags:
            flags.remove("")
            
        if not flags:
            flags_str = "none"
        else:
            # Order them consistently to match expected output formatting if possible
            order = ["wrong_object", "claim_mismatch", "cropped_or_obstructed", "blurry_image", "wrong_angle", "damage_not_visible", "text_instruction_present", "non_original_image", "user_history_risk", "manual_review_required"]
            ordered_flags = [f for f in order if f in flags]
            # Add any other flags that were not in the order list
            for f in flags:
                if f not in ordered_flags:
                    ordered_flags.append(f)
            flags_str = ";".join(ordered_flags)

        return {
            "risk_flags": flags_str
        }
