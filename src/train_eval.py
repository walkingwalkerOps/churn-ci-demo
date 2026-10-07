import json, argparse, pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, recall_score

p = argparse.ArgumentParser()
p.add_argument("--threshold", type=float, default=0.5)
args = p.parse_args()

FEATURES = ["tenure_months", "monthly_charges", "num_support_tickets"]
df = pd.read_csv("data/train.csv")
X_tr, X_te, y_tr, y_te = train_test_split(
    df[FEATURES], df["churned"], test_size=0.25, stratify=df["churned"], random_state=42)

model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
model.fit(X_tr, y_tr)
proba = model.predict_proba(X_te)[:, 1]
metrics = {
    "auc": round(float(roc_auc_score(y_te, proba)), 4),
    "recall": round(float(recall_score(y_te, (proba >= args.threshold).astype(int))), 4),
}
json.dump(metrics, open("metrics.json", "w"), indent=2)
print("metrics:", metrics)
