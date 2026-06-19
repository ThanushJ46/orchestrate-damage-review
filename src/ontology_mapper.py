import logging

logger = logging.getLogger("pipeline")

class OntologyMapper:
    # Taxonomies per category
    TAXONOMY = {
        "car": {
            "parts": {"front_bumper", "rear_bumper", "windshield", "side_mirror", "door", "headlight", "taillight", "body_panel", "unknown"},
            "issues": {"dent", "scratch", "broken_part", "crack", "stain", "unknown", "none"}
        },
        "laptop": {
            "parts": {"screen", "hinge", "keyboard", "corner", "trackpad", "body", "lid", "port", "unknown"},
            "issues": {"crack", "stain", "broken_part", "dent", "liquid_damage", "keys_missing", "unknown", "none"}
        },
        "package": {
            "parts": {"package_corner", "seal", "package_side", "label", "contents", "unknown"},
            "issues": {"crushed_packaging", "torn_packaging", "water_damage", "stain", "missing_item", "damaged_item", "unknown", "none"}
        }
    }

    # Synonym translation maps
    SYNONYMS = {
        # Parts
        "head light": "headlight",
        "front headlight": "headlight",
        "headlights": "headlight",
        "tail light": "taillight",
        "back light": "taillight",
        "taillights": "taillight",
        "front bumper": "front_bumper",
        "front bumper panel": "front_bumper",
        "rear bumper": "rear_bumper",
        "back bumper": "rear_bumper",
        "side mirror": "side_mirror",
        "left side mirror": "side_mirror",
        "right side mirror": "side_mirror",
        "left mirror": "side_mirror",
        "right mirror": "side_mirror",
        "glass": "windshield",
        "windshield glass": "windshield",
        "front glass": "windshield",
        "display": "screen",
        "screen panel": "screen",
        "laptop screen": "screen",
        "hinge area": "hinge",
        "laptop hinge": "hinge",
        "keys": "keyboard",
        "keyboard key": "keyboard",
        "keyboard keys": "keyboard",
        "keys missing": "keyboard",
        "outer body": "body",
        "body edge": "body",
        "laptop body": "body",
        "laptop corner": "corner",
        "corner": "corner",
        "lid area": "lid",
        "laptop lid": "lid",
        "package corner": "package_corner",
        "box corner": "package_corner",
        "cardboard box corner": "package_corner",
        "seal area": "seal",
        "package seal": "seal",
        "box seal": "seal",
        "label": "label",
        "shipping label": "label",
        "address label": "label",
        
        # Issues
        "wet": "water_damage",
        "wetness": "water_damage",
        "wet package": "water_damage",
        "wet box": "water_damage",
        "moisture": "water_damage",
        "scratch": "scratch",
        "scratches": "scratch",
        "mark": "scratch",
        "marks": "scratch",
        "dent": "dent",
        "dents": "dent",
        "crushed": "crushed_packaging",
        "crush": "crushed_packaging",
        "crushed package": "crushed_packaging",
        "crushed box": "crushed_packaging",
        "torn": "torn_packaging",
        "tear": "torn_packaging",
        "torn packaging": "torn_packaging",
        "torn seal": "torn_packaging",
        "torn box": "torn_packaging",
        "liquid stain": "stain",
        "oil stain": "stain",
        "stains": "stain",
        "shattered": "crack",
        "screen crack": "crack",
        "cracked": "crack",
        "broken": "broken_part",
        "missing keys": "keys_missing",
        "key missing": "keys_missing",
        "liquid damage": "liquid_damage"
    }

    @classmethod
    def _levenshtein_match(cls, val: str, allowed: set) -> str:
        # Simple fallback matching: exact check, lowercasing, snake_casing, or prefix match
        cleaned = val.lower().strip().replace(" ", "_")
        if cleaned in allowed:
            return cleaned
        
        # Check if any allowed word is a substring or vice versa
        for allow in allowed:
            if allow in cleaned or cleaned in allow:
                return allow
                
        # Basic edit distance or return 'unknown'
        return "unknown"

    @classmethod
    def standardize_claim(cls, raw_claim: dict) -> dict:
        category = raw_claim.get("object_type", "unknown")
        if category not in cls.TAXONOMY:
            category = "car"  # Default fallback if category not matched
            
        allowed_parts = cls.TAXONOMY[category]["parts"]
        allowed_issues = cls.TAXONOMY[category]["issues"]
        
        raw_part = raw_claim.get("object_part", "unknown").lower().strip()
        raw_issue = raw_claim.get("issue_type", "unknown").lower().strip()
        
        # Translate using synonym mapping
        part = cls.SYNONYMS.get(raw_part, raw_part)
        issue = cls.SYNONYMS.get(raw_issue, raw_issue)
        
        # Align to taxonomy
        std_part = cls._levenshtein_match(part, allowed_parts)
        std_issue = cls._levenshtein_match(issue, allowed_issues)
        
        # Special logic: if the part in laptop is corner and the allowed list has corner, check category
        if category == "laptop" and std_part == "corner":
            std_part = "corner"
        elif category == "package" and (std_part == "corner" or std_part == "package_corner"):
            std_part = "package_corner"

        standardized = {
            "object_type": category,
            "object_part": std_part,
            "issue_type": std_issue,
            "claim_summary": raw_claim.get("claim_summary", ""),
            "severity_hint": raw_claim.get("severity_hint", "unknown")
        }
        
        logger.debug(f"Standardized Claim: {raw_claim} -> {standardized}")
        return standardized

    @classmethod
    def standardize_image(cls, raw_image: dict, category: str) -> dict:
        if category not in cls.TAXONOMY:
            category = "car"
            
        allowed_parts = cls.TAXONOMY[category]["parts"]
        allowed_issues = cls.TAXONOMY[category]["issues"]
        
        raw_parts = raw_image.get("visible_parts", [])
        raw_damage = raw_image.get("visible_damage", "unknown").lower().strip()
        
        std_parts = []
        for p in raw_parts:
            p_clean = p.lower().strip()
            translated = cls.SYNONYMS.get(p_clean, p_clean)
            std_p = cls._levenshtein_match(translated, allowed_parts)
            if std_p != "unknown":
                std_parts.append(std_p)
                
        # Default to unknown if no valid parts visible
        if not std_parts:
            std_parts = ["unknown"]
            
        damage_trans = cls.SYNONYMS.get(raw_damage, raw_damage)
        std_damage = cls._levenshtein_match(damage_trans, allowed_issues)
        
        standardized = {
            "image_id": raw_image.get("image_id", "none"),
            "visible_object": raw_image.get("visible_object", "unknown"),
            "visible_parts": std_parts,
            "visible_damage": std_damage,
            "quality_flags": raw_image.get("quality_flags", []),
            "confidence": raw_image.get("confidence", 0.0),
            "evidence_notes": raw_image.get("evidence_notes", "")
        }
        
        logger.debug(f"Standardized Image: {raw_image} -> {standardized}")
        return standardized
