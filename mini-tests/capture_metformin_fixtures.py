import json, asyncio
from backend.app.knowledge.openfda import _get_json, _cache_key

async def main():
    body = await _get_json("event", 'patient.drug.openfda.generic_name:"metformin"', 2)
    with open("backend/app/tests/fixtures/openfda_event_metformin.json", "w") as f:
        json.dump(body, f, indent=2)
    print(f'Event: {len(body.get("results",[]))} results')

    body2 = await _get_json("label", 'openfda.generic_name:"metformin"', 1)
    with open("backend/app/tests/fixtures/openfda_label_metformin.json", "w") as f:
        json.dump(body2, f, indent=2)
    print(f'Label: {len(body2.get("results",[]))} results')

asyncio.run(main())
