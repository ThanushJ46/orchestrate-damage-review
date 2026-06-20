import os
import mimetypes
import logging
from src.utils import SafeLLMCaller, PipelineConfig, SchemaValidationExceededError

logger = logging.getLogger("pipeline")

IMAGE_ANALYZER_SCHEMA = {
    "type": "object",
    "properties": {
        "image_id": {"type": "string"},
        "visible_object": {"type": "string", "enum": ["car", "laptop", "package", "other", "unknown"]},
        "visible_parts": {
            "type": "array",
            "items": {"type": "string"}
        },
        "visible_damage": {"type": "string"},
        "quality_flags": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["blurry_image", "cropped_or_obstructed", "wrong_angle", "text_instruction_present", "non_original_image", "none"]
            }
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "evidence_notes": {"type": "string"}
    },
    "required": ["image_id", "visible_object", "visible_parts", "visible_damage", "quality_flags", "confidence", "evidence_notes"]
}

class ImageAnalyzer:
    def __init__(self, config: PipelineConfig, prompt_path="prompts/image_analysis.txt"):
        self.config = config
        self.caller = SafeLLMCaller(config)
        
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read()
        else:
            logger.error(f"Prompt file not found at {prompt_path}, using hardcoded baseline instructions.")
            self.system_instruction = "Analyze the image and report the visible object, parts, and damage."

    def analyze_image(self, image_path: str, claim_object: str = None, claim_part: str = None, claim_issue: str = None) -> dict:
        image_id = os.path.basename(image_path).split('.')[0]
        
        if not os.path.exists(image_path):
            logger.warning(f"Image not found at path: {image_path}. Returning fallback payload.")
            return self._get_fallback_payload(image_id, f"File not found: {image_path}")

        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"
            logger.info(f"Loading image '{image_path}' with detected mime-type: {mime_type}")
                
            try:
                file_size = os.path.getsize(image_path)
                logger.info(f"Image file size: {file_size} bytes")
                with open(image_path, "rb") as f:
                    img_data = f.read()
            except IOError as io_err:
                logger.error(f"Failed to read image file at {image_path}. Permission or I/O error: {io_err}")
                return self._get_fallback_payload(image_id, f"Read error: {io_err}")

            image_part = {
                "mime_type": mime_type,
                "data": img_data,
                "image_path": image_path
            }

            prompt_content = f"Please analyze image {image_id}. Return JSON adhering strictly to the schema."
            if claim_object:
                prompt_content += f"\nClaimed Object: {claim_object}"
            if claim_part:
                prompt_content += f"\nClaimed Part: {claim_part}"
            if claim_issue:
                prompt_content += f"\nClaimed Issue: {claim_issue}"
            
            system_instruction = self.system_instruction
            system_instruction = system_instruction.replace("{claimed_object}", claim_object or "unknown")
            system_instruction = system_instruction.replace("{claimed_part}", claim_part or "unknown")
            system_instruction = system_instruction.replace("{claimed_issue}", claim_issue or "unknown")

            parsed = self.caller.call_with_schema(
                system_instruction=system_instruction,
                prompt_content=prompt_content,
                schema=IMAGE_ANALYZER_SCHEMA,
                image_parts=[image_part]
            )
            # Ensure the image_id matches the requested one if the model hallucinated it
            parsed["image_id"] = image_id
            logger.info(f"Successfully analyzed image {image_id}. Object: {parsed.get('visible_object')}, Damage: {parsed.get('visible_damage')}")
            return parsed
        except Exception as e:
            logger.error(f"Failed to analyze image {image_id} via API. Error: {e}")
            raise e

    def _get_fallback_payload(self, image_id: str, error_msg: str) -> dict:
        return {
            "image_id": image_id,
            "visible_object": "unknown",
            "visible_parts": [],
            "visible_damage": "unknown",
            "quality_flags": ["manual_review_required", "damage_not_visible"],
            "confidence": 0.0,
            "evidence_notes": f"Fallback payload triggered. Reason: {error_msg}"
        }
