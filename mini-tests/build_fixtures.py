import json
from copy import deepcopy

# 1. Event fixture where names are missing → triggers merge branches (lines 564/566/568)
e = json.load(open('backend/app/tests/fixtures/openfda_event_197885.json'))
for drug in e['results'][0]['patient']['drug']:
    drug['openfda'] = {'rxcui': drug['openfda'].get('rxcui', ['197885'])}
json.dump(e, open('backend/app/tests/fixtures/openfda_event_197885_no_names.json', 'w'), indent=2)
print('1. openfda_event_197885_no_names.json')

# 2. Event fixture where a drug matches by generic_name → triggers lines 428-429
e2 = json.load(open('backend/app/tests/fixtures/openfda_event_197885.json'))
new_drug = {
    'drugcharacterization': '1',
    'medicinalproduct': 'LISINOPRIL',
    'openfda': {
        'generic_name': ['LISINOPRIL'],
        'brand_name': ['PRINIVIL'],
        'rxcui': ['197885', '197884'],
    }
}
e2['results'][0]['patient']['drug'].insert(0, new_drug)
json.dump(e2, open('backend/app/tests/fixtures/openfda_event_197885_match_generic.json', 'w'), indent=2)
print('2. openfda_event_197885_match_generic.json')
