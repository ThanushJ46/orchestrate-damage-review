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
        self.model_name = gemini_cfg.get("model_name", "gemini-2.5-flash-lite")
        self.fallback_model = gemini_cfg.get("fallback_model", "gemini-2.5-flash-lite")
        self.temperature = gemini_cfg.get("temperature", 0.1)
        self.max_retries = gemini_cfg.get("max_retries", 3)
        self.timeout = gemini_cfg.get("timeout_seconds", 30)
        self.offline_mode = False

        # Load ALL available Gemini API keys for rotation
        self.api_keys = []
        for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3",
                  "GEMINI_API_KEY_4", "GEMINI_API_KEY_5", "GEMINI_API_KEY_6"]:
            val = os.environ.get(k, "").strip()
            if val:
                self.api_keys.append(val)
        self.api_key = self.api_keys[0] if self.api_keys else ""
        logger.info(f"Loaded {len(self.api_keys)} Gemini API key(s) for rotation.")

        # Groq config
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_model = "llama-3.3-70b-versatile"

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
        self._key_index = 0
        if self.config.api_keys:
            genai.configure(api_key=self.config.api_keys[0])
            logger.info(f"ClaimParser: Groq client initialized (model: {self.config.groq_model})")
        else:
            logger.warning("No GEMINI_API_KEY found. Pipeline cannot run.")
            raise RuntimeError("No Gemini API keys configured.")

    def _rotate_key(self) -> bool:
        """Switch to the next available API key. Returns True if switched, False if all exhausted."""
        next_index = self._key_index + 1
        if next_index < len(self.config.api_keys):
            self._key_index = next_index
            new_key = self.config.api_keys[self._key_index]
            genai.configure(api_key=new_key)
            masked = new_key[:6] + "..." + new_key[-4:]
            logger.warning(f"Key {self._key_index-1} exhausted. Rotated to key {self._key_index} ({masked}).")
            return True
        logger.error("ALL Gemini API keys exhausted. Cannot continue.")
        return False

    def check_api_connectivity(self) -> bool:
        """
        Startup diagnostics to check:
        1. API Key present?
        2. Model name configured?
        3. Gemini reachable?
        """
        logger.info("=== Gemini Integration Startup Diagnostics ===")
        
        if self.config.offline_mode:
            logger.warning("Diagnostics: offline_mode is True, but this pipeline requires live API access.")
            return False
            
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
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=15),
        retry=retry_if_exception(is_non_rate_limit_error),
        reraise=True
    )
    def _call_gemini_api(self, model_name: str, system_instruction: str, contents: list) -> str:
        import time
        logger.info("Spacing out Gemini API request by sleeping for 5 seconds to prevent rate limit (429) errors.")
        time.sleep(5)
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
        if self.config.offline_mode:
            raise Exception("Offline mode is not supported. Live API access required.")

        attempts = 0
        rate_limit_attempts = 0
        error_context = ""
        contents = []
        if image_parts:
            # Strip any extra metadata fields (e.g. image_path) that the Gemini SDK doesn't accept
            for part in image_parts:
                clean_part = {k: v for k, v in part.items() if k in ("mime_type", "data")}
                contents.append(clean_part)
        
        while attempts < self.config.max_retries:
            current_prompt = prompt_content
            if error_context:
                current_prompt += f"\n\n[SYSTEM ERROR]: Your previous output failed schema validation: {error_context}. Please fix the output according to the schema."
            
            # Combine current text prompt with any image components
            run_contents = contents + [current_prompt]
            
            try:
                model_to_use = self.config.model_name if attempts < 2 else self.config.fallback_model
                response_text = self._call_gemini_api(model_to_use, system_instruction, run_contents)
                
                parsed_json = json.loads(response_text)
                validate(instance=parsed_json, schema=schema)
                return parsed_json
            except (json.JSONDecodeError, ValidationError, Exception) as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                    # Try rotating to next key immediately — no sleeping
                    rotated = self._rotate_key()
                    if not rotated:
                        raise Exception("ALL Gemini API keys exhausted. Cannot process further images.")
                    # Don't increment attempts — retry same request with new key
                    continue
                attempts += 1
                error_context = str(e)
                logger.warning(f"LLM Call attempt {attempts} failed schema validation. Error: {error_context}")
        
        raise SchemaValidationExceededError(f"Failed to receive valid JSON schema match after {self.config.max_retries} attempts.")
