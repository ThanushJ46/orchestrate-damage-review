import os
import logging
from src.utils import SafeLLMCaller, PipelineConfig, SchemaValidationExceededError

logger = logging.getLogger("pipeline")

CLAIM_PARSER_SCHEMA = {
    "type": "object",
    "properties": {
        "object_type": {"type": "string", "enum": ["car", "laptop", "package", "unknown"]},
        "object_part": {"type": "string"},
        "issue_type": {"type": "string"},
        "claim_summary": {"type": "string"},
        "severity_hint": {"type": "string", "enum": ["low", "medium", "high", "none", "unknown"]}
    },
    "required": ["object_type", "object_part", "issue_type", "claim_summary", "severity_hint"]
}

class ClaimParser:
    def __init__(self, config: PipelineConfig, prompt_path="prompts/claim_extraction.txt"):
        self.config = config
        self.caller = SafeLLMCaller(config)
        
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read()
        else:
            logger.error(f"Prompt file not found at {prompt_path}, using hardcoded baseline instructions.")
            self.system_instruction = "Parse the conversation into standard claim details JSON."

    def parse_claim(self, user_claim: str, claim_object: str) -> dict:
        import copy
        import re
        from src.ontology_mapper import OntologyMapper
        
        # Clean user claim by removing speaker labels to prevent substring matching/context issues
        clean_claim = user_claim
        for label in ["Support:", "Customer:", "Agent:", "Representative:"]:
            clean_claim = re.sub(rf"(?i)\b{label}", "", clean_claim)
            
        prompt_content = f"User Claim: {clean_claim}\nClaim Category: {claim_object}"
        
        # Construct dynamic schema based on claim category
        schema = copy.deepcopy(CLAIM_PARSER_SCHEMA)
        cat = claim_object.lower().strip() if claim_object else "unknown"
        if cat in OntologyMapper.TAXONOMY:
            schema["properties"]["object_type"]["enum"] = [cat, "unknown"]
            schema["properties"]["object_part"]["enum"] = list(OntologyMapper.TAXONOMY[cat]["parts"])
            schema["properties"]["issue_type"]["enum"] = list(OntologyMapper.TAXONOMY[cat]["issues"])
        else:
            all_parts = set()
            all_issues = set()
            for c_tax in OntologyMapper.TAXONOMY.values():
                all_parts.update(c_tax["parts"])
                all_issues.update(c_tax["issues"])
            schema["properties"]["object_part"]["enum"] = list(all_parts)
            schema["properties"]["issue_type"]["enum"] = list(all_issues)
            
        try:
            parsed = self.caller.call_with_schema(
                system_instruction=self.system_instruction,
                prompt_content=prompt_content,
                schema=schema
            )
            logger.info(f"Successfully parsed claim context. Object: {parsed.get('object_type')}, Part: {parsed.get('object_part')}")
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse claim via LLM, using fallback payload. Error: {e}")
            # Fallback parsing using our local cleaner/clean_claim
            obj_type = claim_object if claim_object in ["car", "laptop", "package"] else "unknown"
            
            part = "unknown"
            for p in ["front_bumper", "rear_bumper", "windshield", "side_mirror", "door", "headlight", "taillight", "body_panel", 
                      "screen", "hinge", "keyboard", "corner", "trackpad", "body", "lid", "port",
                      "package_corner", "seal", "package_side", "label", "contents"]:
                p_pat = p.replace("_", r"[\s_]")
                if re.search(rf"(?i)\b{p_pat}\b", clean_claim):
                    part = p
                    break
                    
            issue = "unknown"
            for i in ["dent", "scratch", "broken_part", "broken", "crack", "stain", "liquid_damage", "keys_missing",
                      "crushed_packaging", "torn_packaging", "water_damage", "missing_item", "damaged_item"]:
                i_pat = i.replace("_", r"[\s_]")
                if re.search(rf"(?i)\b{i_pat}\b", clean_claim):
                    issue = "broken_part" if i == "broken" else i
                    break
                    
            return {
                "object_type": obj_type,
                "object_part": part,
                "issue_type": issue,
                "claim_summary": f"Local Fallback. Raw claim: {user_claim[:100]}...",
                "severity_hint": "unknown"
            }
        
