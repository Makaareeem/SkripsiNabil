from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score


DATA_DIR = r"C:\Users\muham\Downloads\Hasil human eval"
DIMS = ["fluency", "factual_correctness", "completeness"]


def icc_absolute(x: np.ndarray) -> tuple[float, float, dict[str, float]]:
    """Shrout-Fleiss/McGraw-Wong absolute-agreement ICC(A,1) and ICC(A,k)."""
    n, k = x.shape
    grand = x.mean()
    row_mean = x.mean(axis=1)
    col_mean = x.mean(axis=0)
    ssr = k * np.sum((row_mean - grand) ** 2)
    ssc = n * np.sum((col_mean - grand) ** 2)
    sse = np.sum((x - row_mean[:, None] - col_mean[None, :] + grand) ** 2)
    msr = ssr / (n - 1)
    msc = ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    icc1 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    icck = (msr - mse) / (msr + (msc - mse) / n)
    return float(icc1), float(icck), {"MSR": float(msr), "MSC": float(msc), "MSE": float(mse)}


def bootstrap_item_mean_ci(x: np.ndarray, seed: int = 20260927, b: int = 20000) -> list[float]:
    rng = np.random.default_rng(seed)
    item_means = x.mean(axis=1)
    idx = rng.integers(0, len(item_means), size=(b, len(item_means)))
    boot = item_means[idx].mean(axis=1)
    return [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]


files = sorted(glob.glob(os.path.join(DATA_DIR, "human_eval_evaluator*_filled.csv")))
dfs = [pd.read_csv(f) for f in files]
base = dfs[0]

checks = {
    "n_files": len(files),
    "shapes": [list(d.shape) for d in dfs],
    "same_eval_id_order": all(np.array_equal(d.eval_id.values, base.eval_id.values) for d in dfs),
    "same_content": {
        col: all(d[col].equals(base[col]) for d in dfs)
        for col in ["No", "eval_id", "Konteks", "Pertanyaan", "Referensi Jawaban", "Jawaban Sistem"]
    },
    "missing_scores": {
        os.path.basename(f): dfs[i][DIMS].isna().sum().to_dict() for i, f in enumerate(files)
    },
}

result: dict[str, object] = {"checks": checks, "dimensions": {}}
item_mean_frame = pd.DataFrame({"eval_id": base.eval_id, "question": base.Pertanyaan})

for di, dim in enumerate(DIMS):
    # items x raters
    x = np.column_stack([d[dim].to_numpy(dtype=float) for d in dfs])
    item_mean_frame[dim] = x.mean(axis=1)
    n, k = x.shape
    per_eval = []
    for j in range(k):
        v = x[:, j]
        per_eval.append({
            "evaluator": j + 1,
            "mean": float(v.mean()),
            "sd": float(v.std(ddof=1)),
            "median": float(np.median(v)),
            "min": float(v.min()),
            "max": float(v.max()),
            "pct_5": float(np.mean(v == 5) * 100),
            "pct_le_2": float(np.mean(v <= 2) * 100),
        })

    flat = x.ravel()
    counts = {str(score): int(np.sum(flat == score)) for score in range(1, 6)}
    exact_all = float(np.mean(np.ptp(x, axis=1) == 0))
    within_one = float(np.mean(np.ptp(x, axis=1) <= 1))
    large_disagreement = float(np.mean(np.ptp(x, axis=1) >= 3))
    item_sd = x.std(axis=1, ddof=1)

    kappas = np.full((k, k), np.nan)
    spearman = np.full((k, k), np.nan)
    for i in range(k):
        for j in range(k):
            if i == j:
                kappas[i, j] = 1
                spearman[i, j] = 1
            elif np.std(x[:, i]) == 0 or np.std(x[:, j]) == 0:
                # Cohen kappa can still be meaningful with one constant rater; rank correlation cannot.
                kappas[i, j] = cohen_kappa_score(x[:, i], x[:, j], weights="quadratic")
            else:
                kappas[i, j] = cohen_kappa_score(x[:, i], x[:, j], weights="quadratic")
                spearman[i, j] = stats.spearmanr(x[:, i], x[:, j]).statistic

    icc1, icck, icc_ms = icc_absolute(x)
    friedman = stats.friedmanchisquare(*[x[:, j] for j in range(k)])
    kendall_w = float(friedman.statistic / (n * (k - 1)))

    # Top disagreements, deterministic: range desc, SD desc, eval_id asc.
    tmp = pd.DataFrame({
        "eval_id": base.eval_id,
        "question": base.Pertanyaan,
        "range": np.ptp(x, axis=1),
        "sd": item_sd,
        "mean": x.mean(axis=1),
    })
    for j in range(k):
        tmp[f"e{j+1}"] = x[:, j]
    top = tmp.sort_values(["range", "sd", "eval_id"], ascending=[False, False, True]).head(10)

    result["dimensions"][dim] = {
        "n_items": n,
        "n_raters": k,
        "overall_mean_all_ratings": float(flat.mean()),
        "item_mean_sd": float(x.mean(axis=1).std(ddof=1)),
        "bootstrap_95ci_item_mean": bootstrap_item_mean_ci(x, seed=20260927 + di),
        "median_all_ratings": float(np.median(flat)),
        "counts": counts,
        "percentages": {s: c / flat.size * 100 for s, c in counts.items()},
        "pct_score_4_or_5": float(np.mean(flat >= 4) * 100),
        "pct_score_5": float(np.mean(flat == 5) * 100),
        "per_evaluator": per_eval,
        "agreement": {
            "exact_all_5": exact_all * 100,
            "range_le_1": within_one * 100,
            "range_ge_3": large_disagreement * 100,
            "mean_within_item_sd": float(item_sd.mean()),
            "pairwise_quadratic_kappa_mean_offdiag": float(np.nanmean(kappas[np.triu_indices(k, 1)])),
            "pairwise_quadratic_kappa_matrix": kappas.tolist(),
            "pairwise_spearman_mean_offdiag": float(np.nanmean(spearman[np.triu_indices(k, 1)])),
            "icc_absolute_single": icc1,
            "icc_absolute_mean_of_5": icck,
            "icc_mean_squares": icc_ms,
            "friedman_chi2": float(friedman.statistic),
            "friedman_p": float(friedman.pvalue),
            "kendall_w": kendall_w,
        },
        "top_disagreements": top.to_dict(orient="records"),
    }

# Cross-dimension relationships based on consensus (mean across raters for each item).
result["consensus_dimension_correlations_pearson"] = item_mean_frame[DIMS].corr(method="pearson").to_dict()
result["consensus_dimension_correlations_spearman"] = item_mean_frame[DIMS].corr(method="spearman").to_dict()

# Notebook-stored group means. Kept separate because the key file was not attached.
group = pd.DataFrame(
    [
        ["gemma2", "base", 4.322222, 4.233333, 4.422222],
        ["gemma2", "finetuned", 3.900000, 4.377778, 4.588889],
        ["llama3.2", "base", 4.600000, 4.000000, 4.033333],
        ["llama3.2", "finetuned", 3.911111, 4.333333, 4.555556],
    ],
    columns=["model", "condition", *DIMS],
)
group["macro_mean"] = group[DIMS].mean(axis=1)
group_records = group.to_dict(orient="records")
condition = group.groupby("condition")[DIMS + ["macro_mean"]].mean()
condition_delta = (condition.loc["finetuned"] - condition.loc["base"]).to_dict()
model_delta = {}
for model, g in group.groupby("model"):
    z = g.set_index("condition")
    model_delta[model] = (z.loc["finetuned", DIMS + ["macro_mean"]] - z.loc["base", DIMS + ["macro_mean"]]).to_dict()
result["notebook_group_means"] = {
    "groups": group_records,
    "condition_means": condition.reset_index().to_dict(orient="records"),
    "finetuned_minus_base": condition_delta,
    "within_model_finetuned_minus_base": model_delta,
}

print(json.dumps(result, ensure_ascii=False, indent=2))
