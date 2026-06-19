# Pipeline Evaluation Report

**Total Evaluated Claims**: 20

## Field Accuracy Metrics

| Field | Correct / Total | Accuracy |
| :--- | :--- | :--- |
| `evidence_standard_met` | 20 / 20 | 100.00% |
| `claim_status` | 20 / 20 | 100.00% |
| `valid_image` | 20 / 20 | 100.00% |
| `severity` | 20 / 20 | 100.00% |
| `issue_type` | 20 / 20 | 100.00% |
| `object_part` | 20 / 20 | 100.00% |

## Detail Comparison & Failure Cases

| User ID | Field | Ground Truth | Prediction | Status |
| :--- | :--- | :--- | :--- | :--- |
| user_001 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_001 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_001 | `valid_image` | `True` | `True` | ✅ Match |
| user_001 | `severity` | `medium` | `medium` | ✅ Match |
| user_001 | `issue_type` | `dent` | `dent` | ✅ Match |
| user_001 | `object_part` | `rear_bumper` | `rear_bumper` | ✅ Match |
| user_002 | `evidence_standard_met` | `False` | `False` | ✅ Match |
| user_002 | `claim_status` | `not_enough_information` | `not_enough_information` | ✅ Match |
| user_002 | `valid_image` | `True` | `True` | ✅ Match |
| user_002 | `severity` | `unknown` | `unknown` | ✅ Match |
| user_002 | `issue_type` | `broken_part` | `broken_part` | ✅ Match |
| user_002 | `object_part` | `front_bumper` | `front_bumper` | ✅ Match |
| user_004 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_004 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_004 | `valid_image` | `True` | `True` | ✅ Match |
| user_004 | `severity` | `medium` | `medium` | ✅ Match |
| user_004 | `issue_type` | `crack` | `crack` | ✅ Match |
| user_004 | `object_part` | `windshield` | `windshield` | ✅ Match |
| user_007 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_007 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_007 | `valid_image` | `True` | `True` | ✅ Match |
| user_007 | `severity` | `medium` | `medium` | ✅ Match |
| user_007 | `issue_type` | `broken_part` | `broken_part` | ✅ Match |
| user_007 | `object_part` | `side_mirror` | `side_mirror` | ✅ Match |
| user_005 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_005 | `claim_status` | `contradicted` | `contradicted` | ✅ Match |
| user_005 | `valid_image` | `True` | `True` | ✅ Match |
| user_005 | `severity` | `low` | `low` | ✅ Match |
| user_005 | `issue_type` | `scratch` | `scratch` | ✅ Match |
| user_005 | `object_part` | `rear_bumper` | `rear_bumper` | ✅ Match |
| user_006 | `evidence_standard_met` | `False` | `False` | ✅ Match |
| user_006 | `claim_status` | `not_enough_information` | `not_enough_information` | ✅ Match |
| user_006 | `valid_image` | `True` | `True` | ✅ Match |
| user_006 | `severity` | `unknown` | `unknown` | ✅ Match |
| user_006 | `issue_type` | `unknown` | `unknown` | ✅ Match |
| user_006 | `object_part` | `headlight` | `headlight` | ✅ Match |
| user_003 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_003 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_003 | `valid_image` | `True` | `True` | ✅ Match |
| user_003 | `severity` | `medium` | `medium` | ✅ Match |
| user_003 | `issue_type` | `dent` | `dent` | ✅ Match |
| user_003 | `object_part` | `door` | `door` | ✅ Match |
| user_008 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_008 | `claim_status` | `contradicted` | `contradicted` | ✅ Match |
| user_008 | `valid_image` | `False` | `False` | ✅ Match |
| user_008 | `severity` | `high` | `high` | ✅ Match |
| user_008 | `issue_type` | `broken_part` | `broken_part` | ✅ Match |
| user_008 | `object_part` | `front_bumper` | `front_bumper` | ✅ Match |
| user_009 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_009 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_009 | `valid_image` | `True` | `True` | ✅ Match |
| user_009 | `severity` | `medium` | `medium` | ✅ Match |
| user_009 | `issue_type` | `crack` | `crack` | ✅ Match |
| user_009 | `object_part` | `screen` | `screen` | ✅ Match |
| user_010 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_010 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_010 | `valid_image` | `True` | `True` | ✅ Match |
| user_010 | `severity` | `medium` | `medium` | ✅ Match |
| user_010 | `issue_type` | `broken_part` | `broken_part` | ✅ Match |
| user_010 | `object_part` | `hinge` | `hinge` | ✅ Match |
| user_011 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_011 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_011 | `valid_image` | `True` | `True` | ✅ Match |
| user_011 | `severity` | `medium` | `medium` | ✅ Match |
| user_011 | `issue_type` | `stain` | `stain` | ✅ Match |
| user_011 | `object_part` | `keyboard` | `keyboard` | ✅ Match |
| user_012 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_012 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_012 | `valid_image` | `True` | `True` | ✅ Match |
| user_012 | `severity` | `low` | `low` | ✅ Match |
| user_012 | `issue_type` | `dent` | `dent` | ✅ Match |
| user_012 | `object_part` | `corner` | `corner` | ✅ Match |
| user_018 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_018 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_018 | `valid_image` | `True` | `True` | ✅ Match |
| user_018 | `severity` | `medium` | `medium` | ✅ Match |
| user_018 | `issue_type` | `crack` | `crack` | ✅ Match |
| user_018 | `object_part` | `screen` | `screen` | ✅ Match |
| user_020 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_020 | `claim_status` | `contradicted` | `contradicted` | ✅ Match |
| user_020 | `valid_image` | `True` | `True` | ✅ Match |
| user_020 | `severity` | `none` | `none` | ✅ Match |
| user_020 | `issue_type` | `none` | `none` | ✅ Match |
| user_020 | `object_part` | `trackpad` | `trackpad` | ✅ Match |
| user_015 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_015 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_015 | `valid_image` | `True` | `True` | ✅ Match |
| user_015 | `severity` | `medium` | `medium` | ✅ Match |
| user_015 | `issue_type` | `crushed_packaging` | `crushed_packaging` | ✅ Match |
| user_015 | `object_part` | `package_corner` | `package_corner` | ✅ Match |
| user_030 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_030 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_030 | `valid_image` | `True` | `True` | ✅ Match |
| user_030 | `severity` | `medium` | `medium` | ✅ Match |
| user_030 | `issue_type` | `torn_packaging` | `torn_packaging` | ✅ Match |
| user_030 | `object_part` | `seal` | `seal` | ✅ Match |
| user_031 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_031 | `claim_status` | `supported` | `supported` | ✅ Match |
| user_031 | `valid_image` | `True` | `True` | ✅ Match |
| user_031 | `severity` | `medium` | `medium` | ✅ Match |
| user_031 | `issue_type` | `water_damage` | `water_damage` | ✅ Match |
| user_031 | `object_part` | `package_side` | `package_side` | ✅ Match |
| user_032 | `evidence_standard_met` | `False` | `False` | ✅ Match |
| user_032 | `claim_status` | `not_enough_information` | `not_enough_information` | ✅ Match |
| user_032 | `valid_image` | `False` | `False` | ✅ Match |
| user_032 | `severity` | `unknown` | `unknown` | ✅ Match |
| user_032 | `issue_type` | `unknown` | `unknown` | ✅ Match |
| user_032 | `object_part` | `contents` | `contents` | ✅ Match |
| user_033 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_033 | `claim_status` | `contradicted` | `contradicted` | ✅ Match |
| user_033 | `valid_image` | `True` | `True` | ✅ Match |
| user_033 | `severity` | `low` | `low` | ✅ Match |
| user_033 | `issue_type` | `unknown` | `unknown` | ✅ Match |
| user_033 | `object_part` | `unknown` | `unknown` | ✅ Match |
| user_034 | `evidence_standard_met` | `True` | `True` | ✅ Match |
| user_034 | `claim_status` | `contradicted` | `contradicted` | ✅ Match |
| user_034 | `valid_image` | `True` | `True` | ✅ Match |
| user_034 | `severity` | `none` | `none` | ✅ Match |
| user_034 | `issue_type` | `none` | `none` | ✅ Match |
| user_034 | `object_part` | `seal` | `seal` | ✅ Match |