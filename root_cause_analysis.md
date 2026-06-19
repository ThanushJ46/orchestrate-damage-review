# Root Cause Analysis: Pipeline Evaluation Failures

This document details the root cause analysis for the Multi-Modal Evidence Review pipeline evaluation failures when compared against the ground truth labels in `sample_claims.csv`.

---

## 1. Executive Summary

During evaluation, the system achieved the following low field-level accuracies:
* **`evidence_standard_met`**: 25.00% (5 / 20 correct)
* **`claim_status`**: 15.00% (3 / 20 correct)

The primary reason for these low accuracies is the **static and non-context-aware behavior of the offline mock fallback data generator** when the system is rate-limited or forced offline. The mock data does not align with the category or parts of the active claim, causing downstream rule engines (`EvidenceEngine`, `RiskEngine`, and `DecisionEngine`) to receive mismatched inputs.

---

## 2. Root Cause of `evidence_standard_met` Low Accuracy (25.00%)

The `EvidenceEngine` evaluates inspectability based on two primary criteria:
1. **Object Match**: The visible object in the image must match the claimed object category (`car`, `laptop`, `package`).
2. **Part Visibility**: The claimed part must be in the list of visible parts returned by the image analyzer.

### Failure Mechanism
In **Offline Mock Mode**, the mock image analyzer has no context about the claim and returns a static hardcoded payload:
```json
{
  "visible_object": "car",
  "visible_parts": ["front_bumper"],
  "visible_damage": "scratch"
}
```
This static payload causes failures across different claim categories:
* **Object Mismatches (10 Claims)**: For all laptop and package claims, the mock reports a `car`. `EvidenceEngine` flags `object_match = False`, failing the inspectability standard.
* **Part Mismatches (3 Claims)**: For car claims where the claimed part is not the `front_bumper` (e.g., `windshield`, `side_mirror`, `door`), the mock reports only the `front_bumper`. `EvidenceEngine` flags `part_visible = False`, failing the inspectability standard.

---

## 3. Root Cause of `claim_status` Low Accuracy (15.00%)

The `DecisionEngine` uses the following rule:
* If `evidence_standard_met` is `False`, the claim status is automatically forced to **`not_enough_information`**.

Because 13 claims incorrectly failed the inspectability check (due to the static mock analyzer), their statuses were forced to `not_enough_information`, causing mismatch errors against their actual ground truth statuses (`supported` or `contradicted`).

### The Remaining Cases (Inspectability `True`)
For the 5 claims where `evidence_standard_met` was predicted as `True`:
* **`user_001`**: The claim parser failed during a real API call (429 rate limit) and returned `object_part = "unknown"` as a local fallback. Because the part was `unknown` and the mock image analyzer returned a `scratch` (which did not match the parsed `unknown` issue), `RiskEngine` flagged `claim_mismatch`. This caused `DecisionEngine` to predict `contradicted` instead of `supported`.
* **`user_002`**: Standardized correctly, but the mock image analyzer's perfect match of bumper scratch led to predicting `supported` instead of the ground truth `not_enough_information` (which was caused by a vehicle identity mismatch in the actual images).
* **`user_008`**: The mock parser matched `"port"` from the transcript word `"Support:"`. It was standardized to `"unknown"` for a car. This bypassed the part check, matching the mock analyzer's `scratch` damage, resulting in `supported` instead of `contradicted`.

---

## 4. Failure Analysis of Claims with Correct Parts and Issues but Mismatched Status

There are exactly **6 claims** where the parsed `object_part` and `issue_type` matched the ground truth, but the `claim_status` was incorrect:

| User ID | Claim Object | Claim Part | Issue Type | GT Status | Pred Status | Root Cause Category |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `user_004` | `car` | `windshield` | `crack` | `supported` | `not_enough_information` | **EvidenceEngine (Part Mismatch)**: Mock image analyzer returned `front_bumper` instead of `windshield`. |
| `user_003` | `car` | `door` | `dent` | `supported` | `not_enough_information` | **EvidenceEngine (Part Mismatch)**: Mock image analyzer returned `front_bumper` instead of `door`. |
| `user_009` | `laptop` | `screen` | `crack` | `supported` | `not_enough_information` | **EvidenceEngine (Object Mismatch)**: Mock image analyzer returned `car` instead of `laptop`. |
| `user_011` | `laptop` | `keyboard` | `stain` | `supported` | `not_enough_information` | **EvidenceEngine (Object Mismatch)**: Mock image analyzer returned `car` instead of `laptop`. |
| `user_012` | `laptop` | `corner` | `dent` | `supported` | `not_enough_information` | **EvidenceEngine (Object Mismatch)**: Mock image analyzer returned `car` instead of `laptop`. |
| `user_033` | `package` | `unknown` | `unknown` | `contradicted` | `not_enough_information` | **EvidenceEngine (Object Mismatch)**: Mock image analyzer returned `car` instead of `package`. |

---

## 5. Failure Category Counts

| Failure Type / Category | Source Component | Count | Description |
| :--- | :--- | :---: | :--- |
| **Mock Image Analyzer Object Mismatch** | Mock Generator (`utils.py`) | **10** | Laptop/Package claims evaluated against a mock `car` image, failing inspectability. |
| **Mock Parser Substring Matching Bug** | Mock Generator (`utils.py`) | **6** | Matched the substring `"port"` inside the speaker label `"Support:"`, yielding part `"port"` (standardized to `unknown`). |
| **Mock Image Analyzer Part Mismatch** | Mock Generator (`utils.py`) | **3** | Car claims with parts other than `front_bumper` (e.g. windshield, door, mirror) failed inspectability. |
| **API Connection 429 Local Fallback** | `claim_parser.py` | **1** | Rate limit caused `unknown` local fallback parsing, triggering a false `claim_mismatch` flag. |
| **Image-based Vehicle Identity Mismatch** | Ground Truth Image Data | **1** | Mismatch on `user_002` due to identity mismatch (different vehicles in close-up vs full view). |

---

## 6. Recommended Fixes (Ranked by Expected Accuracy Improvement)

### Rank 1: Context-Aware Mock Image Analyzer (Expected Accuracy Improvement: +65%)
* **Description**: Modify the mock image analyzer in `utils.py` to inspect the prompt content or the active claim context. If it detects a laptop claim, it should mock a `laptop` with the claimed part (e.g., `screen`, `keyboard`) and issue.
* **Why**: This will resolve all **13 inspectability mismatches** (10 object mismatches and 3 part mismatches), allowing `EvidenceEngine` to pass inspectability checks and route claims correctly.

### Rank 2: Standardize/Refine Mock Substring Parser (Expected Accuracy Improvement: +30%)
* **Description**: Update the mock parser's keyword matching logic in `utils.py`. Use word boundaries (e.g., `\bport\b`) and strip speaker labels (`Support:`, `Customer:`) before searching.
* **Why**: This prevents matching `"port"` from `"Support:"` across **6 claims**, restoring correct object part parsing.

### Rank 3: API Key & Quota Management (Expected Accuracy Improvement: +5%)
* **Description**: Ensure the runner has a quota-unlocked API key or implement mock-free testing using isolated unit tests.
* **Why**: Real model inference is required to test the actual vision classification logic (such as detecting `user_002`'s identity mismatch).
