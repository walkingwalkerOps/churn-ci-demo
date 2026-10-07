import pandas as pd

def test_columns_present():
    df = pd.read_csv("data/train.csv")
    for col in ["tenure_months", "monthly_charges", "num_support_tickets", "churned"]:
        assert col in df.columns

def test_target_is_binary():
    df = pd.read_csv("data/train.csv")
    assert set(df["churned"].unique()) <= {0, 1}
