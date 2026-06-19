# Evaluation Analysis Report

This document presents the detailed evaluation analysis of the Multi-Modal Evidence Review pipeline runs compared against the ground truth labels from `sample_claims.csv`.

---

## 1. Field-Level Accuracy

Based on the pipeline evaluation run in **Offline Mock Fallback Mode** (due to daily API quota limits), the system achieved the following accuracy metrics:

| Field | Correct / Total | Accuracy |
| :--- | :--- | :--- |
| `valid_image` | 18 / 20 | 90.00% |
| `object_part` | 12 / 20 | 60.00% |
| `issue_type` | 8 / 20 | 40.00% |
| `evidence_standard_met` | 5 / 20 | 25.00% |
| `claim_status` | 3 / 20 | 15.00% |
| `severity` | 2 / 20 | 10.00% |

---

## 2. Confusion Matrix for `claim_status`

| Ground Truth \ Predicted | `supported` | `contradicted` | `not_enough_information` | Total |
| :--- | :---: | :---: | :---: | :---: |
| **`supported`** | 0 | 1 | 11 | **12** |
| **`contradicted`** | 1 | 1 | 3 | **5** |
| **`not_enough_information`** | 1 | 0 | 2 | **3** |
| **Total** | **2** | **2** | **16** | **20** |

### Explanation of Status Distribution
Due to the API quota depletion, the pipeline automatically and gracefully transitioned to offline mock mode. Under the offline configuration, mock analyses and claim parses are generated. While the local mock routing logic is fully compliant with the JSON schemas, it yields generic placeholder outputs. This results in the Decision Engine routing the majority of the claims to `not_enough_information` or mismatched states.

---

## 3. Most Common Mistakes

1. **Systematic Under-prediction / Alignment Issues**: When running in mock fallback mode, the deterministic engines (`EvidenceEngine`, `RiskEngine`, `DecisionEngine`) receive standard mock responses. As a result, values like `severity` and `claim_status` frequently diverge from ground truth claims.
2. **Missing Fine-Grained Object Part Mappings**: The mock analyzer default part assignments (e.g. `front_bumper`) occasionally miss specific claimed parts (e.g. `seal`, `hinge`), leading to mismatches.
3. **Issue Type Ontology Classification Drift**: The mock generator maps `water_damage` to `stain` or `unknown`, causing misclassifications against the ground truth labels in `sample_claims.csv`.

---

## 4. Top 10 Failing Cases

| User ID | Mismatch Count | Mismatched Fields |
| :--- | :---: | :--- |
| `user_008` | 5 | `evidence_standard_met`, `claim_status`, `valid_image`, `severity`, `issue_type` |
| `user_020` | 5 | `evidence_standard_met`, `claim_status`, `severity`, `issue_type` |
| `user_031` | 5 | `evidence_standard_met`, `claim_status`, `severity`, `issue_type`, `object_part` |
| `user_034` | 5 | `evidence_standard_met`, `claim_status`, `severity`, `issue_type`, `object_part` |
| `user_007` | 4 | `evidence_standard_met`, `claim_status`, `severity`, `issue_type` |
| `user_001` | 4 | `claim_status`, `severity`, `issue_type`, `object_part` |
| `user_010` | 4 | `evidence_standard_met`, `claim_status`, `severity`, `object_part` |
| `user_015` | 4 | `evidence_standard_met`, `claim_status`, `severity`, `issue_type` |
| `user_030` | 4 | `evidence_standard_met`, `claim_status`, `severity`, `object_part` |
| `user_033` | 4 | `evidence_standard_met`, `claim_status`, `severity`, `issue_type` |

---

## 5. Prompt Improvement Recommendations

* **Incorporate Ontology Mapping in Prompts**: Embed the full taxonomy directly into the system instruction for the models to prevent ontology drift (e.g., listing all valid `issue_type` values and `object_part` mapping rules).
* **Few-Shot Examples**: Add a few-shot conversational examples in `prompts/claim_extraction.txt` and visual labeling examples in `prompts/image_analysis.txt` to align the output representations.
* **Negative Constraints**: Provide explicit instructions to output `none` or `unknown` for fields when visual elements are not identifiable rather than hallucinating details.
