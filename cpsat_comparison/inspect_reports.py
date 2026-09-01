import json, os

schedulers = ['NaiveScheduler', 'EVAGangScheduler', 'StratusScheduler', 'OwlScheduler', 'SynergyScheduler']
base = 'src/simulation_experiments'

for s in schedulers:
    path = os.path.join(base, f'{s}_pai_200', 'report.json')
    try:
        with open(path) as f:
            r = json.load(f)
        print(f"=== {s} ===")
        if isinstance(r, dict):
            print(f"  type: dict, keys: {list(r.keys())}")
            for k, v in r.items():
                if not isinstance(v, (list, dict)):
                    print(f"  {k}: {v}")
        elif isinstance(r, list):
            print(f"  type: list, len={len(r)}")
            if r:
                item = r[0]
                print(f"  first item keys: {list(item.keys()) if isinstance(item, dict) else type(item)}")
                if isinstance(item, dict):
                    for k, v in item.items():
                        if not isinstance(v, (list, dict)):
                            print(f"    {k}: {v}")
        print()
    except Exception as e:
        print(f"{s}: ERROR - {e}")
        print()
