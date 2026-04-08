"""
IS 455 — reusable ML helpers for ml-pipelines notebooks.

- Locates repo `datasets/` from the current working directory (typical: ml-pipelines/).
- Builds sklearn preprocessing + explanatory (linear/logistic) + predictive (random forest).
- Produces metrics, coefficient / importance tables, optional CSV exports under ml-pipelines/artifacts/.

This module is notebook-friendly: no backend/frontend dependencies.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

Task = Literal["classification", "regression"]


def find_repo_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for _ in range(8):
        if (p / "datasets").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise FileNotFoundError(
        "Could not find a `datasets/` folder. Run notebooks with cwd = ml-pipelines/ "
        "or set REPO_ROOT manually."
    )


def datasets_dir() -> Path:
    return find_repo_root() / "datasets"


def artifact_dir() -> Path:
    d = find_repo_root() / "ml-pipelines" / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0}).fillna(0)


def _parse_years_months(text: Any) -> float:
    if pd.isna(text):
        return np.nan
    s = str(text)
    years, months = 0, 0
    if "Years" in s:
        try:
            years = int(s.split("Years")[0].strip())
        except ValueError:
            pass
    if "months" in s:
        try:
            tail = s.split("Years")[-1].replace("months", "").strip()
            months = int(tail)
        except ValueError:
            pass
    return years * 12 + months


def prepare_residents() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    """Risk-focused pipeline: multiclass classification on current_risk_level."""
    path = datasets_dir() / "residents.csv"
    raw = pd.read_csv(path)
    risk_order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    df = raw.copy()
    for c in ["date_of_birth", "date_of_admission", "date_enrolled", "date_closed", "created_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    bool_cols = [c for c in df.columns if c.startswith("sub_cat_")] + [
        "is_pwd",
        "has_special_needs",
        "family_is_4ps",
        "family_solo_parent",
        "family_indigenous",
        "family_parent_pwd",
        "family_informal_settler",
    ]
    for c in bool_cols:
        if c in df.columns:
            df[c] = _to_bool(df[c])
    if "age_upon_admission" in df.columns:
        df["age_upon_admission_months"] = df["age_upon_admission"].apply(_parse_years_months)
    if "present_age" in df.columns:
        df["present_age_months"] = df["present_age"].apply(_parse_years_months)
    if "length_of_stay" in df.columns:
        df["length_of_stay_months"] = df["length_of_stay"].apply(_parse_years_months)
    if {"date_of_admission", "date_enrolled"}.issubset(df.columns):
        df["days_to_enrollment"] = (df["date_enrolled"] - df["date_of_admission"]).dt.days
    if {"date_enrolled", "date_closed"}.issubset(df.columns):
        df["days_enrolled_to_closed"] = (df["date_closed"] - df["date_enrolled"]).dt.days

    y = df["current_risk_level"].astype(str)
    drop = [
        "resident_id",
        "case_control_no",
        "internal_code",
        "current_risk_level",
        "notes_restricted",
    ]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    # Drop raw date columns after engineering
    for c in ["date_of_birth", "date_of_admission", "date_enrolled", "date_closed", "created_at"]:
        if c in X.columns:
            X = X.drop(columns=[c])
    meta = {"name": "residents", "target_description": "current_risk_level (multiclass)"}
    return X, y, "classification", meta


def prepare_safehouses() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    """Predict occupancy pressure: occupancy / capacity."""
    df = pd.read_csv(datasets_dir() / "safehouses.csv")
    df["open_date"] = pd.to_datetime(df["open_date"], errors="coerce")
    df["open_year"] = df["open_date"].dt.year
    cap = df["capacity_girls"].replace(0, np.nan)
    y = (df["current_occupancy"] / cap).clip(0, 2)
    X = df.drop(
        columns=[
            c
            for c in [
                "safehouse_id",
                "safehouse_code",
                "name",
                "notes",
                "current_occupancy",
                "capacity_girls",
                "open_date",
            ]
            if c in df.columns
        ],
        errors="ignore",
    )
    meta = {"name": "safehouses", "target_description": "occupancy / capacity_girls (regression)"}
    return X, y, "regression", meta


def prepare_donations() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    """Predict / explain normalized donation value (estimated_value) from gift metadata.

    Excludes ``amount`` from features: for monetary donations it is effectively the same
    as ``estimated_value`` (near-perfect leakage). Use type, channel, campaign, and dates instead.
    """
    df = pd.read_csv(datasets_dir() / "donations.csv")
    df["donation_date"] = pd.to_datetime(df["donation_date"], errors="coerce")
    df["donation_year"] = df["donation_date"].dt.year
    df["donation_month"] = df["donation_date"].dt.month
    df["has_social_referral"] = df["referral_post_id"].notna().astype(np.int8)
    if "is_recurring" in df.columns:
        df["is_recurring"] = _to_bool(df["is_recurring"])
    y = pd.to_numeric(df["estimated_value"], errors="coerce")
    drop = [
        "donation_id",
        "supporter_id",
        "notes",
        "estimated_value",
        "donation_date",
        "amount",
        "referral_post_id",
    ]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    mask = y.notna()
    X = X.loc[mask].reset_index(drop=True)
    y = y.loc[mask].reset_index(drop=True)
    meta = {"name": "donations", "target_description": "estimated_value (regression; mixed units in source data)"}
    return X, y, "regression", meta


def prepare_donation_allocations() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "donation_allocations.csv")
    df["allocation_date"] = pd.to_datetime(df["allocation_date"], errors="coerce")
    df["alloc_month"] = df["allocation_date"].dt.month
    df["alloc_year"] = df["allocation_date"].dt.year
    y = df["amount_allocated"]
    X = df.drop(
        columns=[
            c
            for c in ["allocation_id", "allocation_notes", "amount_allocated", "allocation_date"]
            if c in df.columns
        ],
        errors="ignore",
    )
    meta = {"name": "donation_allocations", "target_description": "amount_allocated (regression)"}
    return X, y, "regression", meta


def prepare_intervention_plans() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "intervention_plans.csv")
    for c in ["target_date", "case_conference_date", "created_at", "updated_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    df["status"] = df["status"].astype(str)
    y = df["status"]
    drop = ["plan_id", "plan_description", "services_provided", "resident_id", "status"]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    for c in ["target_date", "case_conference_date", "created_at", "updated_at"]:
        if c in X.columns:
            X[c] = (X[c] - pd.Timestamp("2000-01-01")).dt.total_seconds() / 86400.0
    meta = {"name": "intervention_plans", "target_description": "plan status (multiclass classification)"}
    return X, y, "classification", meta


def prepare_incident_reports() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "incident_reports.csv")
    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    df["resolution_date"] = pd.to_datetime(df["resolution_date"], errors="coerce")
    df["days_to_resolve"] = (df["resolution_date"] - df["incident_date"]).dt.days
    sev_map = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    if df["severity"].dtype == object:
        y = df["severity"].map(sev_map).fillna(1)
    else:
        y = df["severity"]
    drop = ["incident_id", "description", "response_taken", "reported_by", "resident_id", "severity"]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    for c in ["incident_date", "resolution_date"]:
        if c in X.columns:
            X = X.drop(columns=[c])
    meta = {"name": "incident_reports", "target_description": "severity (ordinal 0–3, regression for drivers)"}
    return X, y, "regression", meta


def prepare_partner_assignments() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "partner_assignments.csv")
    for c in ["assignment_start", "assignment_end"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    df["assignment_duration_days"] = (df["assignment_end"] - df["assignment_start"]).dt.days
    y = df["status"].astype(str)
    X = df.drop(
        columns=[c for c in ["assignment_id", "responsibility_notes", "status"] if c in df.columns],
        errors="ignore",
    )
    for c in ["assignment_start", "assignment_end"]:
        if c in X.columns:
            X[c] = (X[c] - pd.Timestamp("2000-01-01")).dt.total_seconds() / 86400.0
    meta = {"name": "partner_assignments", "target_description": "assignment status (classification)"}
    return X, y, "classification", meta


def prepare_education_records() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "education_records.csv")
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
    y = df["completion_status"].astype(str)
    X = df.drop(
        columns=[c for c in ["education_record_id", "notes", "school_name", "completion_status"] if c in df.columns],
        errors="ignore",
    )
    if "record_date" in X.columns:
        X["record_date"] = (X["record_date"] - pd.Timestamp("2000-01-01")).dt.total_seconds() / 86400.0
    meta = {"name": "education_records", "target_description": "completion_status (classification)"}
    return X, y, "classification", meta


def prepare_health_wellbeing() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "health_wellbeing_records.csv")
    score_cols = [
        c
        for c in [
            "general_health_score",
            "nutrition_score",
            "sleep_quality_score",
            "energy_level_score",
        ]
        if c in df.columns
    ]
    y = df[score_cols].mean(axis=1)
    X = df.drop(columns=[c for c in ["health_record_id", "notes", "record_date"] + score_cols if c in df.columns], errors="ignore")
    for c in ["medical_checkup_done", "dental_checkup_done"]:
        if c in X.columns:
            X[c] = _to_bool(X[c])
    meta = {"name": "health_wellbeing_records", "target_description": "mean wellbeing score (regression)"}
    return X, y, "regression", meta


def prepare_social_media_posts() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "social_media_posts.csv")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["post_month"] = df["created_at"].dt.month
    df["post_year"] = df["created_at"].dt.year
    # Predict donation lift from content/campaign features (avoid using engagement_rate as both X and y).
    y = df["estimated_donation_value_php"]
    drop = [
        "post_id",
        "platform_post_id",
        "post_url",
        "caption",
        "hashtags",
        "created_at",
        "estimated_donation_value_php",
    ]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    meta = {"name": "social_media_posts", "target_description": "estimated_donation_value_php (regression)"}
    return X, y, "regression", meta


def prepare_process_recordings() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "process_recordings.csv")
    for c in ["concerns_flagged", "referral_made"]:
        if c in df.columns:
            df[c] = _to_bool(df[c])
    if "concerns_flagged" not in df.columns:
        raise ValueError("process_recordings.csv missing concerns_flagged")
    y = df["concerns_flagged"].map({0: "no", 1: "yes"}).astype(str)
    df["session_date"] = pd.to_datetime(df["session_date"], errors="coerce")
    df["session_date_ordinal"] = df["session_date"].map(lambda x: x.toordinal() if pd.notna(x) else np.nan)
    drop = [
        "recording_id",
        "session_narrative",
        "interventions_applied",
        "follow_up_actions",
        "progress_noted",
        "notes_restricted",
        "session_date",
        "concerns_flagged",
    ]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    meta = {"name": "process_recordings", "target_description": "concerns_flagged (classification)"}
    return X, y, "classification", meta


def prepare_home_visitations() -> tuple[pd.DataFrame, pd.Series, Task, dict[str, Any]]:
    df = pd.read_csv(datasets_dir() / "home_visitations.csv")
    for c in ["follow_up_needed", "safety_concerns_noted"]:
        if c in df.columns:
            df[c] = _to_bool(df[c])
    y = df["follow_up_needed"].astype(str)
    drop = [
        "visitation_id",
        "observations",
        "follow_up_notes",
        "visit_date",
        "follow_up_needed",
        "visit_outcome",
    ]
    X = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    meta = {"name": "home_visitations", "target_description": "follow_up_needed (classification)"}
    return X, y, "classification", meta


PIPELINE_REGISTRY: dict[str, Any] = {
    "residents": prepare_residents,
    "safehouses": prepare_safehouses,
    "donations": prepare_donations,
    "donation_allocations": prepare_donation_allocations,
    "intervention_plans": prepare_intervention_plans,
    "incident_reports": prepare_incident_reports,
    "partner_assignments": prepare_partner_assignments,
    "education_records": prepare_education_records,
    "health_wellbeing_records": prepare_health_wellbeing,
    "social_media_posts": prepare_social_media_posts,
    "process_recordings": prepare_process_recordings,
    "home_visitations": prepare_home_visitations,
}


def build_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
    numeric = X_train.select_dtypes(include=[np.number]).columns.tolist()
    categorical = [c for c in X_train.columns if c not in numeric]
    return ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric),
            (
                "cat",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
                categorical,
            ),
        ],
        remainder="drop",
    )


def _stratify_if_possible(y: pd.Series, task: Task):
    if task != "classification":
        return None
    vc = y.value_counts()
    if (vc < 2).any():
        return None
    return y


def _coerce_features(X: pd.DataFrame) -> pd.DataFrame:
    """Imputer + RF dislike raw bool dtypes in some sklearn builds."""
    X = X.copy()
    for col in X.select_dtypes(include=["bool", "boolean"]).columns:
        X[col] = X[col].astype(np.int8)
    return X


def fit_dual_models(
    X: pd.DataFrame,
    y: pd.Series,
    task: Task,
    seed: int = 42,
    test_size: float = 0.25,
) -> dict[str, Any]:
    X = _coerce_features(X)
    strat = _stratify_if_possible(y, task)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=strat)

    pre = build_preprocessor(X_train)
    pre.fit(X_train)

    if task == "regression":
        explanatory = Pipeline(
            [
                ("prep", build_preprocessor(X_train)),
                ("model", LinearRegression()),
            ]
        )
        predictive = Pipeline(
            [
                ("prep", build_preprocessor(X_train)),
                ("model", RandomForestRegressor(n_estimators=200, random_state=seed, min_samples_leaf=1)),
            ]
        )
    else:
        explanatory = Pipeline(
            [
                ("prep", build_preprocessor(X_train)),
                (
                    "model",
                    LogisticRegression(max_iter=2000, random_state=seed),
                ),
            ]
        )
        predictive = Pipeline(
            [
                ("prep", build_preprocessor(X_train)),
                ("model", RandomForestClassifier(n_estimators=300, random_state=seed, min_samples_leaf=1)),
            ]
        )

    explanatory.fit(X_train, y_train)
    predictive.fit(X_train, y_train)

    y_pred_e = explanatory.predict(X_test)
    y_pred_p = predictive.predict(X_test)

    out: dict[str, Any] = {
        "explanatory": explanatory,
        "predictive": predictive,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "y_pred_explanatory": y_pred_e,
        "y_pred_predictive": y_pred_p,
    }

    if task == "regression":
        out["metrics"] = {
            "explanatory_mae": float(mean_absolute_error(y_test, y_pred_e)),
            "explanatory_r2": float(r2_score(y_test, y_pred_e)),
            "predictive_mae": float(mean_absolute_error(y_test, y_pred_p)),
            "predictive_r2": float(r2_score(y_test, y_pred_p)),
        }
    else:
        # Use weighted F1 so binary string labels (e.g. Active/Ended) do not require pos_label.
        f1_avg = "weighted"
        out["metrics"] = {
            "explanatory_accuracy": float(accuracy_score(y_test, y_pred_e)),
            "explanatory_balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred_e)),
            "explanatory_weighted_f1": float(f1_score(y_test, y_pred_e, average=f1_avg, zero_division=0)),
            "predictive_accuracy": float(accuracy_score(y_test, y_pred_p)),
            "predictive_balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred_p)),
            "predictive_weighted_f1": float(f1_score(y_test, y_pred_p, average=f1_avg, zero_division=0)),
        }
        out["classification_report_predictive"] = classification_report(y_test, y_pred_p, zero_division=0)
        out["confusion_matrix_predictive"] = confusion_matrix(y_test, y_pred_p)

    return out


def extract_linear_importance(fitted_pipeline: Pipeline, top: int = 15) -> pd.DataFrame:
    prep: ColumnTransformer = fitted_pipeline.named_steps["prep"]
    model = fitted_pipeline.named_steps["model"]
    names = prep.get_feature_names_out()
    coef = getattr(model, "coef_", None)
    if coef is None:
        return pd.DataFrame()
    if coef.ndim > 1:
        coef = np.mean(np.abs(coef), axis=0)
    else:
        coef = np.abs(coef)
    df = pd.DataFrame({"feature": names, "abs_coefficient": coef}).sort_values("abs_coefficient", ascending=False).head(top)
    return df.reset_index(drop=True)


def extract_forest_importance(fitted_pipeline: Pipeline, top: int = 15) -> pd.DataFrame:
    prep: ColumnTransformer = fitted_pipeline.named_steps["prep"]
    model = fitted_pipeline.named_steps["model"]
    names = prep.get_feature_names_out()
    imp = getattr(model, "feature_importances_", None)
    if imp is None:
        return pd.DataFrame()
    df = pd.DataFrame({"feature": names, "importance": imp}).sort_values("importance", ascending=False).head(top)
    return df.reset_index(drop=True)


def run_pipeline_by_name(name: str, seed: int = 42, save_artifacts: bool = True) -> dict[str, Any]:
    if name not in PIPELINE_REGISTRY:
        raise KeyError(f"Unknown pipeline {name!r}. Choose from: {sorted(PIPELINE_REGISTRY)}")
    X, y, task, meta = PIPELINE_REGISTRY[name]()
    meta = dict(meta)
    print(f"=== {meta['name']} ===")
    print(meta.get("target_description", ""))
    print(f"Shape X={X.shape}, task={task}, n={len(y)}")
    result = fit_dual_models(X, y, task, seed=seed)
    result["meta"] = meta
    result["task"] = task

    print("\n-- Metrics --")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    coef_df = extract_linear_importance(result["explanatory"])
    imp_df = extract_forest_importance(result["predictive"])
    print("\nTop linear drivers (explanatory, |coef| proxy):")
    display_df(coef_df)
    print("\nTop random forest importances (predictive):")
    display_df(imp_df)

    if save_artifacts:
        root = artifact_dir()
        stem = meta["name"]
        pd.DataFrame([result["metrics"]]).to_csv(root / f"{stem}_model_metrics.csv", index=False)
        coef_df.to_csv(root / f"{stem}_top_explanatory_coefficients.csv", index=False)
        imp_df.to_csv(root / f"{stem}_top_features.csv", index=False)
        schema = {
            "pipeline": stem,
            "task": task,
            "target": meta.get("target_description", ""),
            "feature_columns": list(X.columns),
        }
        (root / f"{stem}_model_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
        print(f"\nSaved artifacts under {root}")

    result["explanatory_coefs"] = coef_df
    result["predictive_importance"] = imp_df
    return result


def display_df(df: pd.DataFrame) -> None:
    try:
        from IPython.display import display

        display(df)
    except Exception:
        print(df.to_string(index=False))


@dataclass
class NotebookConfig:
    """Used by blank_notebook.ipynb."""

    pipeline_name: str = "residents"
    seed: int = 42
    save_artifacts: bool = True


def run_notebook_driver(cfg: NotebookConfig | None = None) -> dict[str, Any]:
    cfg = cfg or NotebookConfig()
    return run_pipeline_by_name(cfg.pipeline_name, seed=cfg.seed, save_artifacts=cfg.save_artifacts)
