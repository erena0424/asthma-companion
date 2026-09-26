# Elena Model Deploy Handoff

Production uses **Elena's global XGBClassifier** from `Asthma_binary.ipynb` (branch `Elena`).

## Elena must export (place in `saved_models/`)

| File | Source |
|------|--------|
| `elena_global_model.joblib` | Cell 9 trained `model` |
| `feature_columns.json` | `list(X_train.columns)` after `get_dummies` |
| `daily_merged.csv` (optional) | `daily.to_csv(...)` for merge validation |

Notebook snippet:

```python
import joblib, json
joblib.dump(model, "elena_global_model.joblib")
json.dump(list(X_train.columns), open("feature_columns.json", "w"))
daily.to_csv("daily_merged.csv", index=False)
```

## Your engineering tasks (after export)

1. `model/elena_features.py` — build encoded feature row from API inputs (match notebook)
2. Wire `api/predict.py` → `predict_elena_ml()`
3. Keep `gina_app` for cold-start users without full history
4. Optional: personal edge models in `saved_models/edge_personal_models/model_{user}.joblib`

## Target label (Elena's)

```text
is_flare_up = (actual_puffs >= 3) OR (night AND day AND limit_activity symptoms)
tomorrow_flare_up = shift(-1) of is_flare_up
```
