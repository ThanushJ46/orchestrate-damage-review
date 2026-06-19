import os
import yaml
import logging
import json
import google.generativeai as genai
from jsonschema import validate, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

logger = logging.getLogger("pipeline")

def setup_logging(config_path="config/settings.yaml"):
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        log_cfg = config.get("logging", {})
        level_str = log_cfg.get("level", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        
        log_file = log_cfg.get("log_file_path", "outputs/logs/pipeline.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=level,
            format="[%(asctime)s] [%(levelname)s] [%(filename)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logger.warning(f"Failed to load logging config, using defaults. Error: {e}")

class PipelineConfig:
    def __init__(self, config_path="config/settings.yaml"):
        # Load environment variables from .env if present
        if os.path.exists(".env"):
            try:
                with open(".env", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                key, val = parts[0].strip(), parts[1].strip()
                                # strip quotes if any
                                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                    val = val[1:-1]
                                os.environ[key] = val
            except Exception as e:
                logger.warning(f"Error reading .env file: {e}")

        with open(config_path, "r") as f:
            self.data = yaml.safe_load(f)
        
        # Gemini config
        gemini_cfg = self.data.get("gemini", {})
        self.api_key_env_var = gemini_cfg.get("api_key_env_var", "GEMINI_API_KEY")
        self.api_key = os.environ.get(self.api_key_env_var, "")
        self.model_name = gemini_cfg.get("model_name", "gemini-2.5-flash")
        self.fallback_model = gemini_cfg.get("fallback_model", "gemini-2.5-flash")
        self.temperature = gemini_cfg.get("temperature", 0.1)
        self.max_retries = gemini_cfg.get("max_retries", 3)
        self.timeout = gemini_cfg.get("timeout_seconds", 30)
        self.offline_mode = False

        # Rules
        rules_cfg = self.data.get("rules", {})
        self.confidence_threshold = rules_cfg.get("confidence_threshold", 0.65)
        self.min_required_images = rules_cfg.get("min_required_images", 1)

class SchemaValidationExceededError(Exception):
    pass

try:
    API_ERRORS = (genai.types.APIError, Exception)
except AttributeError:
    try:
        from google.api_core import exceptions
        API_ERRORS = (exceptions.GoogleAPIError, Exception)
    except ImportError:
        API_ERRORS = (Exception,)

def is_non_rate_limit_error(exception):
    err_str = str(exception).lower()
    is_api_err = any(isinstance(exception, t) for t in API_ERRORS)
    is_rate_limit = "429" in err_str or "quota" in err_str or "exhausted" in err_str
    return is_api_err and not is_rate_limit

class SafeLLMCaller:
    def __init__(self, config: PipelineConfig):
        self.config = config
        if self.config.api_key:
            genai.configure(api_key=self.config.api_key)
        else:
            logger.warning("GEMINI_API_KEY environment variable is not set.")
            self.config.offline_mode = True

    def check_api_connectivity(self) -> bool:
        """
        Startup diagnostics to check:
        1. API Key present?
        2. Model name configured?
        3. Gemini reachable?
        """
        logger.info("=== Gemini Integration Startup Diagnostics ===")
        
        # 1. Check Model Name Configured
        model_name = self.config.model_name
        logger.info(f"Diagnostics: Model Name Configured -> '{model_name}'")
        
        # 2. Check API Key Present
        api_key_exists = bool(self.config.api_key)
        if api_key_exists:
            masked_key = self.config.api_key[:6] + "..." + self.config.api_key[-4:] if len(self.config.api_key) > 10 else "PRESENT"
            logger.info(f"Diagnostics: API Key Present -> Yes ({masked_key})")
        else:
            logger.warning("Diagnostics: API Key Present -> No")
            logger.info("==============================================")
            self.config.offline_mode = True
            return False

        # 3. Check Gemini Reachable
        logger.info("Diagnostics: Testing connectivity to Gemini API...")
        for attempt in range(1, 4):
            try:
                model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content("Respond with only the word: OK")
                if response and response.text:
                    logger.info("Diagnostics: Gemini Reachable -> Yes")
                    logger.info("==============================================")
                    self.config.offline_mode = False
                    return True
                else:
                    logger.error("Diagnostics: Gemini Reachable -> No (Empty response)")
                    logger.info("==============================================")
                    self.config.offline_mode = True
                    return False
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                    if attempt < 3:
                        logger.warning(f"Diagnostics: Gemini connectivity check hit rate limit (429). Retrying in 10 seconds (attempt {attempt}/3)...")
                        import time
                        time.sleep(10)
                        continue
                    else:
                        logger.warning("Diagnostics: Gemini connectivity check hit rate limit (429) consistently. Assuming ONLINE but rate-limited.")
                        logger.info("==============================================")
                        self.config.offline_mode = False
                        return True
                logger.error(f"Diagnostics: Gemini Reachable -> No (Error: {e})")
                logger.info("==============================================")
                self.config.offline_mode = True
                return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(is_non_rate_limit_error),
        reraise=True
    )
    def _call_gemini_api(self, model_name: str, system_instruction: str, contents: list) -> str:
        # Construct the model with system instructions
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": self.config.temperature
            },
            system_instruction=system_instruction
        )
        # Call generate_content. contents can include strings and image byte parts
        logger.info(f"Invoking Gemini API ({model_name}). Contents elements: {len(contents)}")
        response = model.generate_content(contents)
        
        if not response:
            logger.error("Received empty response object from Gemini API.")
            raise ValueError("Empty response from Gemini API.")

        try:
            text = response.text
            logger.info(f"Gemini API Response received successfully. Character count: {len(text or '')}")
            logger.debug(f"Gemini API Raw Response: {text}")
            return text
        except ValueError as ve:
            logger.error(f"Failed to retrieve text from Gemini API response. Prompt might be blocked by safety. Error: {ve}")
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                logger.error(f"Prompt feedback: {response.prompt_feedback}")
            if hasattr(response, "candidates") and response.candidates:
                for idx, candidate in enumerate(response.candidates):
                    logger.error(f"Candidate {idx} finish reason: {candidate.finish_reason}")
            raise ve

    def call_with_schema(self, system_instruction: str, prompt_content: str, schema: dict, image_parts: list = None) -> dict:
        is_dry_run = os.environ.get("DRY_RUN", "false").lower() == "true" or not self.config.api_key or self.config.offline_mode
        
        if is_dry_run:
            logger.info("Executing call_with_schema in OFFLINE MOCK MODE.")
            import re
            # 1. Determine prompt type (ClaimParser vs ImageAnalyzer) based on schema properties
            if "object_type" in schema.get("properties", {}):
                obj_type = "car"
                if "laptop" in prompt_content.lower():
                    obj_type = "laptop"
                elif "package" in prompt_content.lower():
                    obj_type = "package"
                
                # Simple extraction of part and issue
                part = "unknown"
                for p in ["front_bumper", "rear_bumper", "windshield", "side_mirror", "door", "headlight", "taillight", "body_panel", 
                          "screen", "hinge", "keyboard", "corner", "trackpad", "body", "lid", "port",
                          "package_corner", "seal", "package_side", "label", "contents"]:
                    if p.replace("_", " ") in prompt_content.lower() or p in prompt_content.lower():
                        part = p
                        break
                        
                issue = "unknown"
                for i in ["dent", "scratch", "broken_part", "crack", "stain", "liquid_damage", "keys_missing",
                          "crushed_packaging", "torn_packaging", "water_damage", "missing_item", "damaged_item"]:
                    if i.replace("_", " ") in prompt_content.lower() or i in prompt_content.lower():
                        issue = i
                        break

                mock_res = {
                    "object_type": obj_type,
                    "object_part": part,
                    "issue_type": issue,
                    "claim_summary": "Mock summary of claim conversation.",
                    "severity_hint": "medium"
                }
                validate(instance=mock_res, schema=schema)
                return mock_res
                
            else:
                # Mock a matching response for ImageAnalyzer
                image_id = "img_1"
                match = re.search(r"image\s+([A-Za-z0-9_]+)", prompt_content)
                if match:
                    image_id = match.group(1)
                
                mock_res = {
                    "image_id": image_id,
                    "visible_object": "car",
                    "visible_parts": ["front_bumper"],
                    "visible_damage": "scratch",
                    "quality_flags": ["none"],
                    "confidence": 0.95,
                    "evidence_notes": "Mocked image analysis indicating inspectable component."
                }
                # Align visible object to what was parsed if possible
                if "laptop" in prompt_content.lower():
                    mock_res["visible_object"] = "laptop"
                    mock_res["visible_parts"] = ["screen"]
                    mock_res["visible_damage"] = "crack"
                elif "package" in prompt_content.lower():
                    mock_res["visible_object"] = "package"
                    mock_res["visible_parts"] = ["package_corner"]
                    mock_res["visible_damage"] = "crushed_packaging"
                
                validate(instance=mock_res, schema=schema)
                return mock_res

        attempts = 0
        rate_limit_attempts = 0
        error_context = ""
        contents = []
        if image_parts:
            contents.extend(image_parts)
        
        while attempts < self.config.max_retries:
            if self.config.offline_mode:
                logger.warning("Offline fallback mode triggered due to rate limit or connection issues.")
                raise SchemaValidationExceededError("Offline mode activated due to persistent rate limits.")

            current_prompt = prompt_content
            if error_context:
                current_prompt += f"\n\n[SYSTEM ERROR]: Your previous output failed schema validation: {error_context}. Please fix the output according to the schema."
            
            # Combine current text prompt with any image components
            run_contents = contents + [current_prompt]
            
            try:
                # Use regular model first, if it fails multiple times, fall back to fallback model
                model_to_use = self.config.model_name if attempts < 2 else self.config.fallback_model
                response_text = self._call_gemini_api(model_to_use, system_instruction, run_contents)
                
                parsed_json = json.loads(response_text)
                validate(instance=parsed_json, schema=schema)
                return parsed_json
            except (json.JSONDecodeError, ValidationError, Exception) as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                    rate_limit_attempts += 1
                    if rate_limit_attempts >= 3:
                        logger.error("Rate limit / Quota exceeded consistently (3 times). Activating graceful degradation to OFFLINE MOCK MODE.")
                        self.config.offline_mode = True
                        raise SchemaValidationExceededError("Rate limit exceeded consistently. Offline mode activated.")
                    
                    logger.warning(f"Rate limit / Quota exceeded (429). Sleeping for 65 seconds before retrying (attempt {rate_limit_attempts}/3)...")
                    import time
                    time.sleep(65)
                    continue
                attempts += 1
                error_context = str(e)
                logger.warning(f"LLM Call attempt {attempts} failed schema validation. Error: {error_context}")
        
        raise SchemaValidationExceededError(f"Failed to receive valid JSON schema match after {self.config.max_retries} attempts.")
