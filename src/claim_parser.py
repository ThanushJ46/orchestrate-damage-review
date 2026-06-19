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
        prompt_content = f"User Claim: {user_claim}\nClaim Category: {claim_object}"
        
        try:
            parsed = self.caller.call_with_schema(
                system_instruction=self.system_instruction,
                prompt_content=prompt_content,
                schema=CLAIM_PARSER_SCHEMA
            )
            logger.info(f"Successfully parsed claim context. Object: {parsed.get('object_type')}, Part: {parsed.get('object_part')}")
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse claim via LLM, using fallback payload. Error: {e}")
            # Fallback parsing
            return {
                "object_type": claim_object if claim_object in ["car", "laptop", "package"] else "unknown",
                "object_part": "unknown",
                "issue_type": "unknown",
                "claim_summary": f"Local Fallback. Raw claim: {user_claim[:100]}...",
                "severity_hint": "unknown"
            }
        
