"""Full-precision rank agreement for the weighting sensitivity (Run 4 figure and value check, 2026-10-15).

master_results.json stores these statistics already rounded (ρ and τ to 4 dp, RMSE to 3 dp). Printing them
again at fewer places double-rounds: the expert ρ is 0.96046 (prints 0.960, not 0.961 from 0.9605) and the
expert RMSE is 6.2502 (prints 6.3, not 6.2 from 6.25). Every text mention reads the values from here,
recomputed from sensitivity_analysis.csv and checked against the stored rounded values.
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from _paths import SRC

_P = SRC / "Data" / "14_Processed_90m" / "sensitivity_analysis.csv"
_MR = json.loads((SRC / "Data" / "master_results.json").read_text(encoding="utf-8"))


def _stats():
    sa = pd.read_csv(_P)
    out = {}
    for k, c, i in (("equal", "Equal", 0), ("expert", "Expert", 1)):
        d = (sa[f"rank_{c}"] - sa.rank_EWM).to_numpy(float)
        out[k] = {"rho": float(stats.spearmanr(sa.rank_EWM, sa[f"rank_{c}"])[0]),
                  "tau": float(stats.kendalltau(sa.rank_EWM, sa[f"rank_{c}"])[0]),
                  "rmse": float(np.sqrt((d ** 2).mean()))}
        ref = _MR["sensitivity"][i]
        assert c in ref["Comparison"]
        assert abs(round(out[k]["rho"], 4) - _MR["sensitivity_rho"][k]) < 1e-9, (k, out[k], _MR["sensitivity_rho"][k])
        assert abs(round(out[k]["rho"], 4) - ref["Spearman ρ"]) < 1e-9
        assert abs(round(out[k]["tau"], 4) - ref["Kendall τ"]) < 1e-9, (k, out[k]["tau"], ref["Kendall τ"])
        assert abs(round(out[k]["rmse"], 3) - ref["RMSE (rank units)"]) < 1e-9, (k, out[k]["rmse"], ref["RMSE (rank units)"])
    return out


SENS = _stats()
SENS_RHO = {k: v["rho"] for k, v in SENS.items()}
