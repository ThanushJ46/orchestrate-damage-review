import pandas as pd

gt = pd.read_csv('official_repo/dataset/sample_claims.csv')
our = pd.read_csv('outputs/output.csv')
claims = pd.read_csv('official_repo/dataset/claims.csv')

ALLOWED_STATUS = {'supported', 'contradicted', 'not_enough_information'}
ALLOWED_ISSUE = {'dent', 'scratch', 'crack', 'glass_shatter', 'broken_part', 'missing_part',
                 'torn_packaging', 'crushed_packaging', 'water_damage', 'stain', 'none', 'unknown', 'keys_missing'}
ALLOWED_SEVERITY = {'none', 'low', 'medium', 'high', 'unknown'}
CAR_PARTS = {'front_bumper','rear_bumper','door','hood','windshield','side_mirror','headlight','taillight','fender','quarter_panel','body','unknown'}
LAPTOP_PARTS = {'screen','keyboard','trackpad','hinge','lid','corner','port','base','body','unknown'}
PACKAGE_PARTS = {'box','package_corner','package_side','seal','label','contents','item','unknown'}

errors = []
for i, row in our.iterrows():
    label = f"Row {i+2} (user={row['user_id']})"
    if row['claim_status'] not in ALLOWED_STATUS:
        errors.append(label + f": BAD claim_status='{row['claim_status']}'")
    if row['issue_type'] not in ALLOWED_ISSUE:
        errors.append(label + f": BAD issue_type='{row['issue_type']}'")
    if str(row['severity']) not in ALLOWED_SEVERITY:
        errors.append(label + f": BAD severity='{row['severity']}'")
    obj = row['claim_object']
    part = row['object_part']
    if obj == 'car' and part not in CAR_PARTS:
        errors.append(label + f": BAD car part='{part}'")
    elif obj == 'laptop' and part not in LAPTOP_PARTS:
        errors.append(label + f": BAD laptop part='{part}'")
    elif obj == 'package' and part not in PACKAGE_PARTS:
        errors.append(label + f": BAD package part='{part}'")

print(f"Total rows in output:    {len(our)}")
print(f"Total rows in claims.csv:{len(claims)}")
print(f"Row count match:         {len(our) == len(claims)}")
print(f"Column order match:      {list(gt.columns) == list(our.columns)}")
print()

# Check if user_id order matches claims.csv
claims_users = list(claims['user_id'])
our_users = list(our['user_id'])
if claims_users == our_users:
    print("User/row ORDER: EXACT MATCH with claims.csv")
else:
    print("User/row ORDER: MISMATCH")
    for idx, (c, o) in enumerate(zip(claims_users, our_users)):
        if c != o:
            print(f"  Row {idx+2}: claims.csv has {c}, our output has {o}")

print()
if errors:
    print(f"VALIDATION ERRORS ({len(errors)} found):")
    for e in errors:
        print(" ", e)
else:
    print("ALL VALUES VALID - no schema violations!")
