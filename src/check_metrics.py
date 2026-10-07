import json, sys, argparse
p = argparse.ArgumentParser()
p.add_argument("--min-recall", type=float, required=True)
args = p.parse_args()

m = json.load(open("metrics.json"))
print(f"recall = {m['recall']:.4f}, required >= {args.min_recall}")
if m["recall"] < args.min_recall:
    print("QUALITY GATE FAILED: recall is below the required minimum")
    sys.exit(1)
print("Quality gate passed")
