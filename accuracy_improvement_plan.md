# Accuracy Improvement Plan

This document outlines deterministic optimizations to improve prediction accuracy for the Multi-Modal Evidence Review pipeline, focusing on `object_part`, `issue_type`, `evidence_standard_met`, and `claim_status` accuracies.

---

## 1. Audit Findings & Diagnostics

### 1.1 ClaimParser Prompts & Schema
* **Current State**: The system prompt contains the taxonomy, but the JSON schema passed to Gemini does not enforce enums for `object_part` or `issue_type`. The model is free to output raw strings (e.g., `"hinge area"`, `"wet surface"`), which rely heavily on post-parsing mappings.
* **Mock Substring Issue**: In offline mode, the substring check matches `"port"` from the word `"Support:"` across 6 package claims, polluting the part extraction.

### 1.2 ImageAnalyzer Prompts & Schema
* **Current State**: The image analyzer prompt runs a generic visual checklist without knowing what object or part is being claimed.
* **Context Mismatch**: The model is asked to list parts blindly. If a claim is for a laptop keyboard, but the image shows the whole laptop and background, the model may return the screen or other parts first, missing the target part or failing to classify it under the correct taxonomy.

### 1.3 OntologyMapper Synonym Coverage
* **Current State**: Several synonym variations found in the dialogue are missing from the `SYNONYMS` translation map, leading to fallback `unknown` mappings.
* **Missing Maps**:
  * `"package surface"` $\rightarrow$ `"package_side"` (Case `user_031`)
  * `"outer corner"` $\rightarrow$ `"corner"` (Case `user_010`)
  * `"wet-looking stain"` / `"wet box"` $\rightarrow$ `"water_damage"`

### 1.4 EvidenceEngine Matching Rules
* **Current State**: If `object_match` is `False`, the engine immediately sets `evidence_standard_met = False`.
* **Incorrect Behavior**: In case `user_033` (package claim, but image shows a car component), the ground truth has `evidence_standard_met = True` and `claim_status = contradicted`. This means severe cross-category mismatches (e.g. package vs car) are considered "inspectable" enough to confirm a contradiction, whereas vehicle identity mismatches (e.g. different car) are not.

### 1.5 DecisionEngine Logic
* **Current State**: If `evidence_standard_met` is `False`, the decision status is hardcoded to `not_enough_information`.
* **Incorrect Behavior**: Category mismatches (e.g. laptop claim with car photo) should lead to `contradicted`, not `not_enough_information`.

---

## 2. Proposed Improvements & Rankings

| Proposed Optimization | Affected Fields | Expected Leaderboard Impact | Implementation Effort | Description |
| :--- | :--- | :---: | :---: | :--- |
| **1. Dynamic JSON Schema Enums for ClaimParser** | `object_part`, `issue_type` | **High** | **Low** | Dynamically restrict the JSON schema enums passed to Gemini based on the claim category. If category is `car`, only allow car parts/issues. |
| **2. Context-Aware Visual Prompting & Schema for ImageAnalyzer** | `evidence_standard_met`, `claim_status` | **High** | **Medium** | Pass the claimed category and part to the image analyzer prompt. Dynamically restrict `visible_parts` schema enums to match the category. |
| **3. Align DecisionEngine with Strict Truth Table** | `claim_status` | **High** | **Low** | Update `decision_engine.py` to route category mismatches to `contradicted` instead of hardcoding `not_enough_information` for all inspectability failures. |
| **4. Refine EvidenceEngine Inspectability Rules** | `evidence_standard_met` | **Medium** | **Low** | Distinguish between cross-category mismatches (which meet the standard to contradict) and intra-category identity mismatches (which do not). |
| **5. Clean Speaker Tags & Regex Boundaries in Mock Parser** | `object_part` | **Medium** | **Low** | Pre-process dialogue transcripts to strip speaker tags (e.g., `Support:`) and use word boundaries (`\bport\b`) to prevent false matches. |
| **6. OntologyMapper Synonym Expansion** | `object_part`, `issue_type` | **Low** | **Low** | Add missing synonyms (`package surface`, `outer corner`, `wet-looking stain`) to the `SYNONYMS` lookup table. |

---

## 3. Implementation Details

### 3.1 Dynamic JSON Schema for ClaimParser
Modify `claim_parser.py` to generate the schema dynamically:
```python
        schema = copy.deepcopy(CLAIM_PARSER_SCHEMA)
        if claim_object in OntologyMapper.TAXONOMY:
            schema["properties"]["object_part"]["enum"] = list(OntologyMapper.TAXONOMY[claim_object]["parts"])
            schema["properties"]["issue_type"]["enum"] = list(OntologyMapper.TAXONOMY[claim_object]["issues"])
```

### 3.2 Context-Aware Image Analysis
Update `image_analyzer.py`'s signature:
```python
    def analyze_image(self, image_path: str, claim_object: str = None, claim_part: str = None) -> dict:
```
Update prompt content to guide Gemini:
```python
        prompt_content = f"Analyze image {image_id} for a claim involving a '{claim_object}'."
        if claim_part and claim_part != "unknown":
            prompt_content += f" Specifically check the '{claim_part}' for damage."
```
Dynamically update `IMAGE_ANALYZER_SCHEMA` enums based on `claim_object`.

### 3.3 Strict Decision Engine Mapping
Update `decision_engine.py` to handle category mismatches:
```python
        if not evidence_met:
            if "wrong_object" in risk_flags and "claim_mismatch" in risk_flags:
                # Absolute category mismatch (e.g. laptop claim showing a car)
                claim_status = "contradicted"
                severity = "low"
                justification = "The visual evidence contradicts the claim: the image shows a completely different object category."
            else:
                claim_status = "not_enough_information"
                ...
```
