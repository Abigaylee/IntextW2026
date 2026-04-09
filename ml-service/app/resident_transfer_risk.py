"""Resident transfer-risk scoring: live PostgreSQL + notebook-aligned features (see resident_transfer_risk_pipeline)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.db_access import fetch_dataframe

# PostgreSQL allows '-infinity' / 'infinity' on timestamp columns; pandas cannot parse them.
_PG_TS_SENTINELS = frozenset({'-infinity', 'infinity', '+infinity', '-inf', '+inf', 'inf'})


def _is_likely_date_column(name: str) -> bool:
    n = str(name).lower()
    if n in ('created_at', 'updated_at', 'modified_at'):
        return True
    return 'date' in n


def _scrub_pg_infinity_in_object_columns(df: pd.DataFrame) -> None:
    """Replace PG timestamp infinity strings in any object/string column (in-place)."""
    for col in df.columns:
        ser = df[col]
        if ser.dtype != object and getattr(ser.dtype, 'name', '') != 'string':
            continue
        try:
            sl = ser.astype(str).str.strip().str.lower()
            bad = sl.isin(_PG_TS_SENTINELS)
            if bad.any():
                df[col] = ser.where(~bad, pd.NaT)
        except Exception:
            continue


def _coerce_ts_value(v: Any) -> Any:
    """Single-cell timestamp parse; never raises (returns NaT on failure)."""
    if v is None or v is pd.NA:
        return pd.NaT
    if isinstance(v, float) and pd.isna(v):
        return pd.NaT
    if isinstance(v, str):
        t = v.strip().lower()
        if t in _PG_TS_SENTINELS or t in ('none', 'nat', ''):
            return pd.NaT
    if isinstance(v, pd.Timestamp):
        try:
            if pd.isna(v) or v.year < 1:
                return pd.NaT
        except Exception:
            return pd.NaT
        return v
    try:
        ts = pd.Timestamp(v)
        if pd.isna(ts) or ts.year < 1:
            return pd.NaT
        return ts
    except Exception:
        return pd.NaT


def _coerce_datetime_series(s: pd.Series) -> pd.Series:
    """Parse timestamps for modeling; map PG infinity and out-of-range values to NaT."""
    if s.empty:
        return pd.to_datetime(s, errors='coerce')
    s = s.copy()
    if s.dtype == object or getattr(s.dtype, 'name', '') == 'string':
        try:
            sl = s.astype(str).str.strip().str.lower()
            bad = sl.isin(_PG_TS_SENTINELS) | sl.isin({'none', 'nat', ''})
            s = s.mask(bad, pd.NaT)
        except Exception:
            pass
    try:
        out = pd.to_datetime(s, errors='coerce', utc=False)
    except Exception:
        out = s.map(_coerce_ts_value)
        out = pd.to_datetime(out, errors='coerce')
    # Some pandas versions raise only after partial convert; map any remaining problem cells
    if out.isna().all() and s.notna().any():
        out = s.map(_coerce_ts_value)
        out = pd.to_datetime(out, errors='coerce')
    try:
        yn = out.dt.year
        out = out.mask(yn.notna() & (yn < 1), pd.NaT)
    except (AttributeError, TypeError, ValueError):
        pass
    return out


def _coerce_likely_date_columns(df: pd.DataFrame) -> None:
    """Coerce every column whose name suggests a date (covers SELECT * on residents)."""
    for c in list(df.columns):
        if _is_likely_date_column(str(c)) and c in df.columns:
            df[c] = _coerce_datetime_series(df[c])


PREDICTION_WINDOW_DAYS = 30
SEVERITY_MAP = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}

LEAKAGE_COLS = [
    'target_transferred',
    'case_status',
    'resident_id',
    'case_control_no',
    'internal_code',
    'date_closed',
    'days_enrolled_to_closed',
    'notes_restricted',
    'created_at',
    'reintegration_status',
]

# PG date/timestamptz can hold -infinity/infinity; psycopg cannot load those into Python (DataError).
_PG_INF_TEXT = "('-infinity', 'infinity', '+infinity')"


def _safe_date_col(name: str) -> str:
    return (
        f'CASE WHEN ({name})::text IN {_PG_INF_TEXT} THEN NULL::date ELSE {name} END AS {name}'
    )


def _safe_timestamptz_col(name: str) -> str:
    return (
        f'CASE WHEN ({name})::text IN {_PG_INF_TEXT} THEN NULL::timestamptz ELSE {name} END AS {name}'
    )


# Explicit columns: SELECT * would still fetch created_at / dates as PG infinities and fail in psycopg.
RESIDENTS_SQL = f"""
SELECT
    resident_id,
    case_control_no,
    internal_code,
    safehouse_id,
    case_status,
    sex,
    {_safe_date_col('date_of_birth')},
    birth_status,
    place_of_birth,
    religion,
    case_category,
    sub_cat_orphaned,
    sub_cat_trafficked,
    sub_cat_child_labor,
    sub_cat_physical_abuse,
    sub_cat_sexual_abuse,
    sub_cat_osaec,
    sub_cat_cicl,
    sub_cat_at_risk,
    sub_cat_street_child,
    sub_cat_child_with_hiv,
    is_pwd,
    pwd_type,
    has_special_needs,
    special_needs_diagnosis,
    family_is_4ps,
    family_solo_parent,
    family_indigenous,
    family_parent_pwd,
    family_informal_settler,
    {_safe_date_col('date_of_admission')},
    age_upon_admission,
    present_age,
    length_of_stay,
    referral_source,
    referring_agency_person,
    {_safe_date_col('date_colb_registered')},
    {_safe_date_col('date_colb_obtained')},
    assigned_social_worker,
    initial_case_assessment,
    {_safe_date_col('date_case_study_prepared')},
    reintegration_type,
    reintegration_status,
    initial_risk_level,
    current_risk_level,
    {_safe_date_col('date_enrolled')},
    {_safe_date_col('date_closed')},
    {_safe_timestamptz_col('created_at')},
    notes_restricted
FROM residents
"""

INCIDENTS_SQL = f"""
SELECT
    incident_id,
    resident_id,
    CASE
        WHEN incident_date::text IN {_PG_INF_TEXT} THEN NULL::timestamp
        ELSE incident_date::timestamp
    END AS incident_date,
    severity::text AS severity,
    resolved,
    follow_up_required
FROM incident_reports
"""

EDUCATION_SQL = f"""
SELECT
    education_record_id,
    resident_id,
    CASE
        WHEN record_date::text IN {_PG_INF_TEXT} THEN NULL::timestamp
        ELSE record_date::timestamp
    END AS record_date,
    education_level,
    school_name,
    enrollment_status,
    attendance_rate,
    progress_percent,
    completion_status::text AS completion_status
FROM education_records
"""


def _service_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return _service_root().parent


def _resolve_model_path() -> Path:
    env = (os.getenv('RESIDENT_TRANSFER_RISK_MODEL_PATH') or '').strip()
    if env:
        return Path(env)
    service = _service_root()
    for p in (
        service / 'artifacts' / 'resident_transfer_risk_model.joblib',
        _repo_root() / 'ml-pipelines' / 'artifacts' / 'resident_transfer_risk_model.joblib',
    ):
        if p.is_file():
            return p
    return service / 'artifacts' / 'resident_transfer_risk_model.joblib'


def _resolve_metrics_path() -> Path:
    env = (os.getenv('RESIDENT_TRANSFER_RISK_METRICS_PATH') or '').strip()
    if env:
        return Path(env)
    service = _service_root()
    for p in (
        service / 'artifacts' / 'resident_transfer_risk_metrics.csv',
        _repo_root() / 'ml-pipelines' / 'artifacts' / 'resident_transfer_risk_metrics.csv',
    ):
        if p.is_file():
            return p
    return service / 'artifacts' / 'resident_transfer_risk_metrics.csv'


def _safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        if pd.isna(value):
            return 0
        return int(value)
    except Exception:
        return 0


def _boolish_to_num(s: pd.Series) -> pd.Series:
    def one(x: Any) -> int:
        if x is True:
            return 1
        if x is False:
            return 0
        t = str(x).strip().lower()
        if t in ('true', '1', 'yes', 't'):
            return 1
        return 0

    return s.map(one)


def _series_to_float64(s: pd.Series) -> pd.Series:
    """psycopg returns PostgreSQL numeric as Decimal; pandas/sklearn need float64."""
    return pd.to_numeric(s, errors='coerce').astype('float64')


def _coerce_numeric_agg_frame(df: pd.DataFrame, key_col: str = 'resident_id') -> None:
    """In-place: every non-key column to float64 (counts/ratios/means from groupby)."""
    for c in df.columns:
        if c == key_col:
            continue
        df[c] = _series_to_float64(df[c])


def _engineer_joined_active(res: pd.DataFrame, inc: pd.DataFrame, edu: pd.DataFrame) -> pd.DataFrame:
    """Active residents only; same 30-day incident/education windows as the training notebook."""
    if res.empty:
        return pd.DataFrame()

    cs = res['case_status'].astype(str).str.strip().str.lower()
    base = res[cs == 'active'].copy()
    if base.empty:
        return pd.DataFrame()

    base = base[base['date_enrolled'].notna()].copy()
    if base.empty:
        return pd.DataFrame()

    base['prediction_cutoff_date'] = base['date_enrolled'] + pd.Timedelta(days=PREDICTION_WINDOW_DAYS)

    edu = edu.copy()
    for _col in ('attendance_rate', 'progress_percent'):
        if _col in edu.columns:
            edu[_col] = _series_to_float64(edu[_col])

    inc2 = inc.copy()
    if not inc2.empty and 'severity' in inc2.columns:
        inc2['severity_num'] = inc2['severity'].map(SEVERITY_MAP)
    else:
        inc2['severity_num'] = pd.NA

    if 'resolved' in inc2.columns:
        inc2['resolved_num'] = _boolish_to_num(inc2['resolved'])
    else:
        inc2['resolved_num'] = 0

    if 'follow_up_required' in inc2.columns:
        inc2['follow_up_num'] = _boolish_to_num(inc2['follow_up_required'])
    else:
        inc2['follow_up_num'] = 0

    inc2['unresolved_high'] = ((inc2['resolved_num'] == 0) & (inc2['severity_num'] >= 3)).astype(int)

    inc30 = base[['resident_id', 'date_enrolled', 'prediction_cutoff_date']].merge(inc2, on='resident_id', how='left')
    inc30 = inc30[
        inc30['incident_date'].notna()
        & inc30['date_enrolled'].notna()
        & (inc30['incident_date'] >= inc30['date_enrolled'])
        & (inc30['incident_date'] <= inc30['prediction_cutoff_date'])
    ].copy()

    inc_agg = inc30.groupby('resident_id', as_index=False).agg(
        incident_count_30d=('incident_id', 'count'),
        incident_severity_mean_30d=('severity_num', 'mean'),
        incident_severity_max_30d=('severity_num', 'max'),
        unresolved_ratio_30d=(
            'resolved_num',
            lambda s: 1.0 - float(pd.to_numeric(s, errors='coerce').fillna(0).mean()),
        ),
        unresolved_high_count_30d=('unresolved_high', 'sum'),
        follow_up_ratio_30d=('follow_up_num', 'mean'),
    )
    _coerce_numeric_agg_frame(inc_agg)

    edu30 = base[['resident_id', 'date_enrolled', 'prediction_cutoff_date']].merge(edu, on='resident_id', how='left')
    edu30 = edu30[
        edu30['record_date'].notna()
        & edu30['date_enrolled'].notna()
        & (edu30['record_date'] >= edu30['date_enrolled'])
        & (edu30['record_date'] <= edu30['prediction_cutoff_date'])
    ].copy()

    edu_agg = edu30.sort_values(['resident_id', 'record_date']).groupby('resident_id', as_index=False).agg(
        edu_records_30d=('education_record_id', 'count'),
        attendance_mean_30d=('attendance_rate', 'mean'),
        attendance_last_30d=('attendance_rate', 'last'),
        progress_mean_30d=('progress_percent', 'mean'),
        progress_last_30d=('progress_percent', 'last'),
    )
    _coerce_numeric_agg_frame(edu_agg)
    edu_agg['progress_delta_30d'] = edu_agg['progress_last_30d'] - edu_agg['progress_mean_30d']
    edu_agg['attendance_delta_30d'] = edu_agg['attendance_last_30d'] - edu_agg['attendance_mean_30d']

    joined = base.merge(inc_agg, on='resident_id', how='left').merge(edu_agg, on='resident_id', how='left')
    return joined


def _model_metrics_from_csv(metrics_path: Path) -> dict[str, Any] | None:
    if not metrics_path.is_file():
        return None
    try:
        mdf = pd.read_csv(metrics_path)
        if len(mdf) == 0:
            return None
        row = mdf.iloc[0]
        return {
            'selectedModel': str(row.get('selected_model', '')),
            'threshold': _safe_float(row.get('threshold')),
            'rocAuc': _safe_float(row.get('roc_auc')),
            'avgPrecision': _safe_float(row.get('avg_precision')),
            'precisionAtThreshold': _safe_float(row.get('precision_at_threshold')),
            'recallAtThreshold': _safe_float(row.get('recall_at_threshold')),
            'f1AtThreshold': _safe_float(row.get('f1_at_threshold')),
        }
    except Exception:
        return None


def _risk_tier_from_probabilities(proba: pd.Series) -> pd.Series:
    """Map probabilities to tier labels as plain object dtype (never Categorical — fillna('Unknown') breaks on Categorical)."""
    p = pd.to_numeric(proba, errors='coerce')
    binned = pd.cut(p, bins=[-0.001, 0.5, 0.75, 1.0], labels=['Monitor', 'Medium', 'High'])
    out: list[str] = []
    for v in binned.tolist():
        out.append('Unknown' if pd.isna(v) else str(v))
    return pd.Series(out, index=proba.index, dtype=object)


def _normalize_tier_series_for_counts(s: pd.Series) -> pd.Series:
    """Safe tier labels for value_counts (Categorical cannot gain 'Unknown' without add_categories)."""

    def _one_tier_label(v: Any) -> str:
        if v is None:
            return 'Unknown'
        if isinstance(v, float) and pd.isna(v):
            return 'Unknown'
        t = str(v).strip()
        if not t or t.lower() in ('nan', '<na>', 'none', 'nat'):
            return 'Unknown'
        return t

    if pd.api.types.is_categorical_dtype(s):
        s = s.astype(object)
    return s.map(_one_tier_label)


def _pack_scored_response(
    scored: pd.DataFrame,
    tier_col: str,
    metrics_path: Path,
    data_source: str,
    load_warning: str = '',
) -> dict[str, Any]:
    tier_counts: list[dict[str, Any]] = []
    tier_vc = _normalize_tier_series_for_counts(scored[tier_col])
    for label, count in tier_vc.value_counts().items():
        tier_counts.append({'tier': str(label), 'count': int(count)})

    top_residents: list[dict[str, Any]] = []
    has_ids = all(c in scored.columns for c in ('resident_id', 'case_control_no'))
    if has_ids:
        tier_rank = {'high': 3, 'medium': 2, 'monitor': 1}
        ranked = scored.copy()
        ranked['__tier_rank'] = ranked[tier_col].astype(str).str.strip().str.lower().map(tier_rank).fillna(0)
        ranked = ranked.sort_values(['__tier_rank', 'pred_transfer_prob'], ascending=[False, False]).head(5)
        for _, row in ranked.iterrows():
            top_residents.append(
                {
                    'residentId': _safe_int(row.get('resident_id')),
                    'caseControlNo': str(row.get('case_control_no') or ''),
                    'internalCode': str(row.get('internal_code') or ''),
                    'assignedSocialWorker': str(row.get('assigned_social_worker') or ''),
                    'safehouseId': str(row.get('safehouse_id') or ''),
                    'riskTier': str(row.get(tier_col) or ''),
                    'predTransferProb': round(_safe_float(row.get('pred_transfer_prob')), 4),
                }
            )

    n = int(len(scored))
    high_count = int(scored[tier_col].astype(str).str.strip().str.lower().eq('high').sum())
    high_share = round(high_count / n, 4) if n else 0.0
    avg_prob = round(float(scored['pred_transfer_prob'].mean()), 4) if n else 0.0

    return {
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'dataSource': data_source,
        'loadWarning': load_warning,
        'endpointVersion': '1.1.0',
        'question': 'Which residents are at risk of transfer instead of closure?',
        'summary': {
            'scoredResidents': n,
            'highRiskResidents': high_count,
            'highRiskShare': high_share,
            'avgTransferProbability': avg_prob,
        },
        'modelMetrics': _model_metrics_from_csv(metrics_path),
        'riskTierCounts': tier_counts,
        'topResidents': top_residents,
    }


def build_resident_transfer_risk_summary_from_database(conn: str) -> dict[str, Any]:
    """Score **active** residents using the bundled sklearn pipeline and live DB rows."""
    res = fetch_dataframe(conn, RESIDENTS_SQL)
    inc = fetch_dataframe(conn, INCIDENTS_SQL)
    edu = fetch_dataframe(conn, EDUCATION_SQL)

    # PG infinity can appear in any text or timestamp column; scrub before parsing.
    _scrub_pg_infinity_in_object_columns(res)
    _scrub_pg_infinity_in_object_columns(inc)
    _scrub_pg_infinity_in_object_columns(edu)
    _coerce_likely_date_columns(res)
    _coerce_likely_date_columns(inc)
    _coerce_likely_date_columns(edu)

    joined = _engineer_joined_active(res, inc, edu)
    if not joined.empty:
        _scrub_pg_infinity_in_object_columns(joined)
        _coerce_likely_date_columns(joined)

    if joined.columns.duplicated().any():
        joined = joined.loc[:, ~joined.columns.duplicated()].copy()

    if joined.empty:
        return {
            'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
            'dataSource': 'database',
            'loadWarning': 'No active residents with a known enrollment date to score.',
            'endpointVersion': '1.1.0',
            'question': 'Which residents are at risk of transfer instead of closure?',
            'summary': {
                'scoredResidents': 0,
                'highRiskResidents': 0,
                'highRiskShare': 0.0,
                'avgTransferProbability': 0.0,
            },
            'modelMetrics': _model_metrics_from_csv(_resolve_metrics_path()),
            'riskTierCounts': [],
            'topResidents': [],
        }

    model_path = _resolve_model_path()
    if not model_path.is_file():
        raise FileNotFoundError(f'Resident transfer risk model not found: {model_path}')

    pipeline = joblib.load(model_path)

    meta_cols = ['resident_id', 'case_control_no', 'internal_code', 'assigned_social_worker', 'safehouse_id']
    for c in meta_cols:
        if c not in joined.columns:
            joined[c] = ''

    X = joined.drop(columns=[c for c in LEAKAGE_COLS if c in joined.columns], errors='ignore')
    for c in list(X.columns):
        if str(X[c].dtype).startswith('datetime64'):
            X = X.drop(columns=[c])

    if hasattr(pipeline, 'feature_names_in_') and getattr(pipeline, 'feature_names_in_', None) is not None:
        X = X.reindex(columns=list(pipeline.feature_names_in_))

    # Categorical dtypes confuse some sklearn transformers; pipeline expects str/number.
    for c in list(X.columns):
        if pd.api.types.is_categorical_dtype(X[c]):
            X[c] = X[c].astype(str).replace({'<NA>': '', 'nan': ''})

    proba = pipeline.predict_proba(X)[:, 1]
    scored = joined[meta_cols].reset_index(drop=True).copy()
    scored['pred_transfer_prob'] = pd.to_numeric(proba, errors='coerce').astype('float64')
    scored['risk_tier'] = _risk_tier_from_probabilities(scored['pred_transfer_prob'])
    tier_col = 'risk_tier'

    return _pack_scored_response(
        scored,
        tier_col,
        _resolve_metrics_path(),
        'database',
        '',
    )
