# Dataset Analysis

This document provides a comprehensive analysis of the CSV files provided in the `data/` directory for the orchestrate damage review project.

## 1. CSV Files and Columns Overview

The dataset consists of five CSV files. Here is the column breakdown for each:

### `claims.csv`
- `user_id`: Identifier for the user making the claim.
- `image_paths`: Semicolon-separated list of file paths to the images uploaded as evidence.
- `user_claim`: The transcript of the conversation between the customer and support agent, separated by `|`.
- `claim_object`: The general category of the item being claimed (e.g., `car`, `laptop`, `package`).

### `sample_claims.csv`
- `user_id`: Identifier for the user making the claim.
- `image_paths`: Semicolon-separated list of file paths to the images.
- `user_claim`: Transcript of the conversation.
- `claim_object`: Category of the item.
- `evidence_standard_met`: Boolean indicating if the images satisfy the visual evidence requirements (`true`/`false`).
- `evidence_standard_met_reason`: Explanation of why the evidence standard is or is not met.
- `risk_flags`: Semicolon-separated list of identified risks (e.g., fraud, poor image quality).
- `issue_type`: The specific category of damage observed (e.g., `dent`, `scratch`, `crack`).
- `object_part`: The specific component of the object that is damaged (e.g., `rear_bumper`, `screen`, `seal`).
- `claim_status`: The final decision on the claim (`supported`, `contradicted`, `not_enough_information`).
- `claim_status_justification`: Text explaining the reason behind the final `claim_status`.
- `supporting_image_ids`: Identifiers of the specific images that prove the claim (e.g., `img_1`), or `none`.
- `valid_image`: Boolean indicating if the image is considered valid (`true`/`false`).
- `severity`: The severity level of the damage (`low`, `medium`, `high`, `none`, `unknown`).

### `output.csv`
This file contains the exact same headers as `sample_claims.csv` but is currently empty. It is the target file where the final predictions will be written.

### `user_history.csv`
- `user_id`: Identifier for the user.
- `past_claim_count`: Total number of claims the user has submitted historically.
- `accept_claim`: Number of the user's past claims that were accepted.
- `manual_review_claim`: Number of the user's past claims that required manual review.
- `rejected_claim`: Number of the user's past claims that were rejected.
- `last_90_days_claim_count`: Number of claims submitted by the user in the last 90 days.
- `history_flags`: Risk flags derived from the user's history (e.g., `none`, `user_history_risk`, `manual_review_required`).
- `history_summary`: A textual summary describing the user's historical risk profile.

### `evidence_requirements.csv`
- `requirement_id`: A unique ID for the specific evidence rule.
- `claim_object`: The category of item the rule applies to (`all`, `car`, `laptop`, `package`).
- `applies_to`: The specific damage type or part the rule applies to.
- `minimum_image_evidence`: The detailed textual rule explaining what must be visible in the images.

---

## 2. Meaning of Each Column

*   **Inputs:** `user_id`, `image_paths`, `user_claim`, `claim_object` provide the context of the current claim.
*   **Outputs (Predictions):** Columns like `evidence_standard_met`, `claim_status`, `issue_type`, `object_part`, and `severity` are decisions that must be derived by analyzing the images, claim text, user history, and evidence requirements.
*   **Context/Rules:** The `user_history.csv` metrics and `evidence_requirements.csv` rules act as external knowledge bases that inform the prediction values.

---

## 3. Relationships Between Files

1.  **`claims.csv` -> `output.csv`**: `claims.csv` is the evaluation dataset. A system must read each row in `claims.csv`, analyze it, and write the expanded row (with all 10 predicted fields) into `output.csv`.
2.  **`sample_claims.csv`**: This is a labeled reference file. It demonstrates the expected input-output mappings and can be used for few-shot prompting to guide the model's output formatting and reasoning.
3.  **`user_history.csv`**: This table must be joined with the claims data via the `user_id` column to determine if the claimant has a risky history, which affects the predicted `risk_flags` and `claim_status`.
4.  **`evidence_requirements.csv`**: This table acts as a rulebook. The `claim_object` in `claims.csv` is used to filter which rules apply to the current claim, dictating whether `evidence_standard_met` should be true or false based on the images.

---

## 4. How Claims Connect to Users

Claims are linked to users via the **`user_id`** column. For any row in `claims.csv` or `sample_claims.csv`, the corresponding user's history can be found by looking up that exact `user_id` in `user_history.csv`. For example, if a claim is from `user_005`, we must check `user_history.csv` for `user_005` to see that they have `user_history_risk` due to several exaggerated claims. This risk flag must be incorporated into the final prediction.

---

## 5. How Images Are Referenced

Images are referenced in two distinct formats:
1.  **Input format (`image_paths`)**: Full file paths separated by semicolons. Example: `images/test/case_001/img_1.jpg;images/test/case_001/img_2.jpg`.
2.  **Output format (`supporting_image_ids`)**: Base names without extensions, indicating which specific images support the claim. If multiple images support the claim, they are separated by semicolons (e.g., `img_1;img_2`). If no image supports the claim, the value is `"none"`.

---

## 6. Which Fields Are Inputs

When processing a new claim, the system only has access to the following fields directly from `claims.csv`:
*   `user_id`
*   `image_paths`
*   `user_claim`
*   `claim_object`

Additionally, external inputs accessed via lookups include:
*   The actual image files located at `image_paths`.
*   The user's historical data from `user_history.csv`.
*   The applicable rules from `evidence_requirements.csv`.

---

## 7. Which Fields Must Be Predicted

The system must output the following fields to complete `output.csv`:
1.  `evidence_standard_met`
2.  `evidence_standard_met_reason`
3.  `risk_flags`
4.  `issue_type`
5.  `object_part`
6.  `claim_status`
7.  `claim_status_justification`
8.  `supporting_image_ids`
9.  `valid_image`
10. `severity`

---

## 8. Valid Values for Labels

Based on the data in `sample_claims.csv`, the output fields generally expect the following valid values:

*   **`evidence_standard_met`**: `"true"`, `"false"`
*   **`valid_image`**: `"true"`, `"false"`
*   **`claim_status`**: `"supported"`, `"contradicted"`, `"not_enough_information"`
*   **`severity`**: `"low"`, `"medium"`, `"high"`, `"none"`, `"unknown"`
*   **`supporting_image_ids`**: e.g., `"img_1"`, `"img_2"`, `"img_1;img_2"`, `"none"`
*   **`risk_flags`**: A semicolon-separated list (or `"none"`) comprising values such as:
    *   `none`
    *   `user_history_risk`
    *   `manual_review_required`
    *   `wrong_object`
    *   `claim_mismatch`
    *   `wrong_angle`
    *   `damage_not_visible`
    *   `non_original_image`
    *   `blurry_image`
    *   `cropped_or_obstructed`
    *   `text_instruction_present`
*   **`issue_type`**: e.g., `"dent"`, `"scratch"`, `"broken_part"`, `"crack"`, `"stain"`, `"crushed_packaging"`, `"torn_packaging"`, `"water_damage"`, `"unknown"`, `"none"`
*   **`object_part`**: e.g., `"rear_bumper"`, `"front_bumper"`, `"windshield"`, `"side_mirror"`, `"door"`, `"headlight"`, `"screen"`, `"hinge"`, `"keyboard"`, `"corner"`, `"trackpad"`, `"package_corner"`, `"seal"`, `"package_side"`, `"contents"`, `"unknown"`

---

## 9. Inconsistencies and Missing Information

*   **Multilingual Text**: The `user_claim` field contains conversational transcripts in mixed languages (e.g., English, Spanish, Hindi, Chinese Pinyin). The system must be capable of understanding multilingual input to extract the correct claim context.
*   **Transcript Formatting**: The `user_claim` is a single string where different speakers are separated by the `|` character (e.g., `Customer: ... | Support: ...`). This requires parsing to isolate the customer's actual complaint.
*   **Empty Validations**: In cases where `claim_status` is `contradicted` or `not_enough_information`, the fields `issue_type` and `object_part` are sometimes filled with `"unknown"`, but in other cases, they specify the actual missing or undamaged part (e.g., `issue_type: "none"`, `object_part: "trackpad"`).
*   **Image Availability**: The paths in `image_paths` (e.g., `images/test/case_001/img_1.jpg`) reference local files. The system must verify if these images exist in the local directory structure or if they need to be fetched/mocked during execution.
