import os
import re
import json
import logging
import copy
from src.utils import PipelineConfig, SchemaValidationExceededError

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

        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read()
        else:
            logger.error(f"Prompt file not found at {prompt_path}, using hardcoded baseline instructions.")
            self.system_instruction = "Parse the conversation into standard claim details JSON."

        # Initialize Groq client if key is available
        self._groq_client = None
        if self.config.groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.config.groq_api_key)
                logger.info(f"ClaimParser: Groq client initialized (model: {self.config.groq_model})")
            except Exception as e:
                logger.warning(f"ClaimParser: Failed to initialize Groq client: {e}. Will fall back to Gemini.")

        # Keep SafeLLMCaller for connectivity check and Gemini fallback
        from src.utils import SafeLLMCaller
        self.caller = SafeLLMCaller(config)

    def _call_groq(self, prompt_content: str, schema: dict) -> dict:
        """Call Groq API with structured JSON output."""
        from jsonschema import validate, ValidationError

        # Build the allowed values hint from schema for better accuracy
        obj_part_enum = schema["properties"].get("object_part", {}).get("enum", [])
        issue_enum = schema["properties"].get("issue_type", {}).get("enum", [])
        obj_enum = schema["properties"].get("object_type", {}).get("enum", [])

        enum_hints = ""
        if obj_part_enum:
            enum_hints += f"\nAllowed object_part values: {obj_part_enum}"
        if issue_enum:
            enum_hints += f"\nAllowed issue_type values: {issue_enum}"
        if obj_enum:
            enum_hints += f"\nAllowed object_type values: {obj_enum}"

        system_msg = self.system_instruction + enum_hints + \
            "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no code blocks, no explanation."

        for attempt in range(3):
            try:
                response = self._groq_client.chat.completions.create(
                    model=self.config.groq_model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt_content}
                    ],
                    temperature=0.1,
                    max_tokens=512,
                    response_format={"type": "json_object"}
                )
                raw_text = response.choices[0].message.content.strip()
                logger.info(f"[DEFENSIVE LOG] Groq ClaimParser raw output: {raw_text[:300]}")

                parsed = json.loads(raw_text)
                # If Groq returns an array, take the first element
                if isinstance(parsed, list):
                    parsed = parsed[0] if parsed else {}
                # Enforce allowed values: if value has comma (multiple parts), pick first valid one
                def clamp_to_enum(val, allowed):
                    if val in allowed:
                        return val
                    # Try splitting on comma and picking first match
                    for candidate in str(val).replace(" ", "").split(","):
                        candidate = candidate.strip()
                        if candidate in allowed:
                            return candidate
                    # Try snake_case normalization
                    normalized = str(val).lower().strip().replace(" ", "_")
                    if normalized in allowed:
                        return normalized
                    return "unknown"

                if obj_part_enum:
                    parsed["object_part"] = clamp_to_enum(parsed.get("object_part", "unknown"), obj_part_enum)
                if issue_enum:
                    parsed["issue_type"] = clamp_to_enum(parsed.get("issue_type", "unknown"), issue_enum)

                validate(instance=parsed, schema=schema)
                return parsed

            except Exception as e:
                logger.warning(f"Groq ClaimParser attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise

    def parse_claim(self, user_claim: str, claim_object: str) -> dict:
        from src.ontology_mapper import OntologyMapper

        # Strip speaker labels to prevent substring matching/context noise
        clean_claim = user_claim
        for label in ["Support:", "Customer:", "Agent:", "Representative:"]:
            clean_claim = re.sub(rf"(?i)\b{re.escape(label)}", "", clean_claim)

        prompt_content = f"User Claim: {clean_claim}\nClaim Category: {claim_object}"

        # Build dynamic schema based on claim category
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

        # Try Groq first (fast, free, text-only)
        if self._groq_client:
            try:
                parsed = self._call_groq(prompt_content, schema)
                logger.info(f"[Groq] Parsed claim: object={parsed.get('object_type')}, part={parsed.get('object_part')}, issue={parsed.get('issue_type')}")
                return parsed
            except Exception as e:
                logger.warning(f"Groq ClaimParser failed, falling back to Gemini. Error: {e}")

        # Fallback: Gemini via SafeLLMCaller
        try:
            parsed = self.caller.call_with_schema(
                system_instruction=self.system_instruction,
                prompt_content=prompt_content,
                schema=schema
            )
            logger.info(f"[Gemini] Parsed claim: object={parsed.get('object_type')}, part={parsed.get('object_part')}, issue={parsed.get('issue_type')}")
            return parsed
        except Exception as e:
            logger.error(f"Both Groq and Gemini failed for claim parsing. Error: {e}")
            raise Exception("Claim parsing requires live API access. Both primary and fallback APIs failed.")
