import os
import requests

# ---- Config ----
BASE_URL = "http://api.statistiken.bundesbank.de/rest/data/"
SERIES = {
    "BBSIS/M.I.ZST.ZI.EUR.S1311.B.A604.R005X.R.A.A._Z._Z.A": "Zinsstrukturkurve_05_Y.csv",
    "BBSIS/M.I.ZST.ZI.EUR.S1311.B.A604.R01XX.R.A.A._Z._Z.A": "Zinsstrukturkurve_1_Y.csv",
    "BBSIS/M.I.ZST.ZI.EUR.S1311.B.A604.R05XX.R.A.A._Z._Z.A": "Zinsstrukturkurve_5_Y.csv",
    "BBSIS/M.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A": "Zinsstrukturkurve_10_Y.csv"
}
FORMAT = "?format=csv"

# Resolve save path: one folder above current, into data_raw/
save_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "data_raw"))
os.makedirs(save_dir, exist_ok=True)

# ---- Download loop ----
for series, filename in SERIES.items():
    url = BASE_URL + series + FORMAT
    filepath = os.path.join(save_dir, filename)

    print(f"Downloading {series} -> {filename} ...")
    r = requests.get(url)
    if r.status_code == 200:
        with open(filepath, "wb") as f:
            f.write(r.content)
        print(f"✅ Saved: {filepath}")
    else:
        print(f"❌ Failed ({r.status_code}): {url}")