import numpy as np, pandas as pd, sys
rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 42)
n = 3000
tenure = rng.gamma(2.0, 12.0, n).clip(0, 72)
charges = rng.normal(70, 25, n).clip(15, 200)
tickets = rng.poisson(1.2, n).clip(0, 15)
z = -0.08*tenure + 0.04*charges + 0.7*tickets - 3.0
churned = (rng.uniform(0, 1, n) < 1/(1+np.exp(-z))).astype(int)
pd.DataFrame({"tenure_months": tenure.round(3), "monthly_charges": charges.round(3),
              "num_support_tickets": tickets, "churned": churned}).to_csv("data/train.csv", index=False)
print("wrote data/train.csv", n, "rows, churn rate", round(churned.mean(), 3))
