"""
Tier-1 program analytics for Reports & analytics: residents, education, health & wellbeing.
Prefers live PostgreSQL (same connection as social media: SOCIAL_MEDIA_DB_URL or
ConnectionStrings__DefaultConnection), falls back to datasets/*.csv. Notebook artifacts
still supply top drivers and model metadata.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.db_access import fetch_dataframe, resolve_db_connection_value

RESIDENTS_SQL = """
SELECT
    resident_id,
    safehouse_id,
    case_status::text AS case_status,
    current_risk_level::text AS current_risk_level,
    reintegration_status::text AS reintegration_status,
    date_closed
FROM residents
"""

EDUCATION_SQL = """
SELECT
    education_record_id,
    resident_id,
    record_date,
    education_level,
    school_name,
    enrollment_status,
    attendance_rate,
    progress_percent,
    completion_status::text AS completion_status
FROM education_records
"""

HEALTH_SQL = """
SELECT
    health_record_id,
    resident_id,
    record_date,
    general_health_score,
    nutrition_score,
    sleep_quality_score,
    energy_level_score,
    height_cm,
    weight_kg,
    medical_checkup_done,
    dental_checkup_done,
    psychological_checkup_done
FROM health_wellbeing_records
"""

SAFEHOUSE_METRICS_SQL = """
SELECT
    safehouse_id,
    month_start,
    month_end,
    active_residents,
    avg_education_progress,
    avg_health_score,
    process_recording_count,
    home_visitation_count,
    incident_count,
    notes
FROM safehouse_monthly_metrics
"""


def _normalize_frame_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    return out


def _read_csv_normalized(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return _normalize_frame_columns(df)


def _load_residents_frame(root: Path) -> tuple[pd.DataFrame, str, str]:
    csv_path = Path(os.getenv('RESIDENTS_DATASET_PATH', str(root / 'datasets' / 'residents.csv')))
    conn = resolve_db_connection_value()
    if conn:
        try:
            df = fetch_dataframe(conn, RESIDENTS_SQL)
            return df, 'database', ''
        except Exception as ex:
            err = str(ex)
            if csv_path.is_file():
                try:
                    return _read_csv_normalized(csv_path), 'csv', f'Database query failed ({err}); using CSV fallback.'
                except Exception as ex2:
                    return pd.DataFrame(), 'error', f'Database: {err}; CSV: {ex2}'
            return pd.DataFrame(), 'database-error', err
    if csv_path.is_file():
        try:
            return _read_csv_normalized(csv_path), 'csv', ''
        except Exception as ex:
            return pd.DataFrame(), 'error', str(ex)
    return pd.DataFrame(), 'missing-file', f'No database URL and residents CSV missing: {csv_path}'


def _load_education_frame(root: Path) -> tuple[pd.DataFrame, str, str]:
    csv_path = Path(os.getenv('EDUCATION_DATASET_PATH', str(root / 'datasets' / 'education_records.csv')))
    conn = resolve_db_connection_value()
    if conn:
        try:
            df = fetch_dataframe(conn, EDUCATION_SQL)
            return df, 'database', ''
        except Exception as ex:
            err = str(ex)
            if csv_path.is_file():
                try:
                    return _read_csv_normalized(csv_path), 'csv', f'Database query failed ({err}); using CSV fallback.'
                except Exception as ex2:
                    return pd.DataFrame(), 'error', f'Database: {err}; CSV: {ex2}'
            return pd.DataFrame(), 'database-error', err
    if csv_path.is_file():
        try:
            return _read_csv_normalized(csv_path), 'csv', ''
        except Exception as ex:
            return pd.DataFrame(), 'error', str(ex)
    return pd.DataFrame(), 'missing-file', f'No database URL and education CSV missing: {csv_path}'


def _load_health_frame(root: Path) -> tuple[pd.DataFrame, str, str]:
    csv_path = Path(
        os.getenv('HEALTH_WELLBEING_DATASET_PATH', str(root / 'datasets' / 'health_wellbeing_records.csv'))
    )
    conn = resolve_db_connection_value()
    if conn:
        try:
            df = fetch_dataframe(conn, HEALTH_SQL)
            return df, 'database', ''
        except Exception as ex:
            err = str(ex)
            if csv_path.is_file():
                try:
                    return _read_csv_normalized(csv_path), 'csv', f'Database query failed ({err}); using CSV fallback.'
                except Exception as ex2:
                    return pd.DataFrame(), 'error', f'Database: {err}; CSV: {ex2}'
            return pd.DataFrame(), 'database-error', err
    if csv_path.is_file():
        try:
            return _read_csv_normalized(csv_path), 'csv', ''
        except Exception as ex:
            return pd.DataFrame(), 'error', str(ex)
    return pd.DataFrame(), 'missing-file', f'No database URL and health CSV missing: {csv_path}'


def _load_safehouse_metrics_frame(root: Path) -> tuple[pd.DataFrame, str, str]:
    csv_path = Path(os.getenv('SAFEHOUSE_MONTHLY_METRICS_PATH', str(root / 'datasets' / 'safehouse_monthly_metrics.csv')))
    conn = resolve_db_connection_value()
    if conn:
        try:
            df = fetch_dataframe(conn, SAFEHOUSE_METRICS_SQL)
            return _normalize_frame_columns(df), 'database-pipeline', ''
        except Exception as ex:
            err = str(ex)
            if csv_path.is_file():
                try:
                    return _read_csv_normalized(csv_path), 'csv-pipeline', f'Database query failed ({err}); using pipeline CSV fallback.'
                except Exception as ex2:
                    return pd.DataFrame(), 'error', f'Database: {err}; CSV: {ex2}'
            return pd.DataFrame(), 'database-error', err
    if csv_path.is_file():
        try:
            return _read_csv_normalized(csv_path), 'csv-pipeline', ''
        except Exception as ex:
            return pd.DataFrame(), 'error', str(ex)
    return pd.DataFrame(), 'missing-file', f'No database URL and safehouse metrics CSV missing: {csv_path}'


def _append_live_note(model_note: str | None, data_source: str) -> str | None:
    if data_source != 'database':
        return model_note
    extra = ' Live data from PostgreSQL.'
    return (model_note + extra) if model_note else extra.strip()


def _repo_root(ml_service_dir: Path) -> Path:
    return ml_service_dir.resolve().parent


def _artifacts(ml_service_dir: Path) -> Path:
    return _repo_root(ml_service_dir) / 'ml-pipelines' / 'artifacts'


def _humanize_feature(raw: str) -> str:
    s = (raw or '').strip()
    if not s or s.lower().startswith('unnamed'):
        return s
    s = re.sub(r'^(cat__|num__)', '', s)
    s = s.replace('__', ' · ').replace('_', ' ')
    return s[:80] + ('…' if len(s) > 80 else '')


def _read_top_features(path: Path, max_n: int = 8) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        df = pd.read_csv(path)
    except Exception:
        return []

    if df.empty:
        return []

    # residents / standard
    if 'feature' in df.columns and 'importance' in df.columns:
        df = df.sort_values('importance', ascending=False)
        out = []
        for _, row in df.head(max_n).iterrows():
            label = _humanize_feature(str(row['feature']))
            if not label:
                continue
            out.append({'label': label, 'importance': round(float(row['importance']), 6)})
        return out

    # education
    if 'feature' in df.columns and 'rf_importance_agg' in df.columns:
        df = df.sort_values('rf_importance_agg', ascending=False)
        out = []
        for _, row in df.head(max_n).iterrows():
            label = _humanize_feature(str(row['feature']))
            if label.lower() == 'resident id':
                continue
            if not label:
                continue
            out.append({'label': label, 'importance': round(float(row['rf_importance_agg']), 6)})
        return out

    # health (first column unnamed)
    imp_col = 'importance' if 'importance' in df.columns else None
    if imp_col:
        feat_col = [c for c in df.columns if c != imp_col][0]
        df = df.sort_values(imp_col, ascending=False)
        out = []
        for _, row in df.head(max_n).iterrows():
            label = _humanize_feature(str(row[feat_col]))
            if not label:
                continue
            out.append({'label': label, 'importance': round(float(row[imp_col]), 6)})
        return out

    return []


def _share_counts(counts: dict[str, int]) -> list[dict[str, Any]]:
    total = max(sum(counts.values()), 1)
    rows = []
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        rows.append({'label': str(k) if k else 'Unknown', 'count': int(v), 'share': round(v / total, 4)})
    return rows


def _empty_section(data_source: str, load_warning: str) -> dict[str, Any]:
    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': {},
        'chartRows': [],
        'secondaryChartRows': [],
        'safehouseRows': [],
        'topDrivers': [],
        'pipelineTarget': None,
        'modelNote': None,
        'businessQuestion': None,
        'modelQuality': None,
    }


def _empty_residents_section(data_source: str, load_warning: str) -> dict[str, Any]:
    d = _empty_section(data_source, load_warning)
    d['summary'] = {'totalResidents': 0, 'activeResidents': 0, 'distinctSafehouses': 0}
    return d


def _empty_education_section(data_source: str, load_warning: str) -> dict[str, Any]:
    d = _empty_section(data_source, load_warning)
    d['summary'] = {
        'totalRecords': 0,
        'uniqueResidents': 0,
        'avgAttendancePercent': None,
        'avgProgressPercent': None,
    }
    return d


def _empty_health_section(data_source: str, load_warning: str) -> dict[str, Any]:
    d = _empty_section(data_source, load_warning)
    d['summary'] = {
        'totalRecords': 0,
        'uniqueResidents': 0,
        'avgGeneralHealthScore': None,
        'medianGeneralHealthScore': None,
        'avgNutritionScore': None,
        'avgSleepQualityScore': None,
        'avgEnergyLevelScore': None,
        'medicalCheckupShare': None,
        'dentalCheckupShare': None,
        'psychologicalCheckupShare': None,
    }
    return d


def _empty_safehouse_performance_section(data_source: str, load_warning: str) -> dict[str, Any]:
    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': {
            'safehouseCount': 0,
            'latestMonth': None,
        },
        'rows': [],
        'topSafehouses': [],
        'bottomSafehouses': [],
    }


def _empty_reintegration_section(data_source: str, load_warning: str) -> dict[str, Any]:
    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': {
            'lookbackMonths': 12,
            'successCount': 0,
            'eligibleCount': 0,
            'successRate': 0.0,
        },
        'monthlyTrend': [],
    }


def build_residents_section(root: Path, art: Path) -> dict[str, Any]:
    schema_path = art / 'residents_model_schema.json'
    features_path = art / 'residents_top_features.csv'

    df, data_source, load_warning = _load_residents_frame(root)

    if data_source == 'missing-file':
        return _empty_residents_section('missing-file', load_warning)

    if data_source in ('error', 'database-error') and df.empty:
        return _empty_residents_section(data_source, load_warning)

    if df.empty:
        return _empty_residents_section(data_source if data_source in ('database', 'csv') else 'empty', load_warning)

    pipeline_target = None
    if schema_path.is_file():
        try:
            schema = json.loads(schema_path.read_text(encoding='utf-8'))
            pipeline_target = schema.get('target')
        except Exception:
            pass

    risk_col = 'current_risk_level' if 'current_risk_level' in df.columns else None
    risk_counts: dict[str, int] = {}
    if risk_col:
        for v in df[risk_col].fillna('Unknown').astype(str):
            risk_counts[v] = risk_counts.get(v, 0) + 1
    chart_rows = _share_counts(risk_counts)

    status_counts: dict[str, int] = {}
    if 'case_status' in df.columns:
        for v in df['case_status'].fillna('Unknown').astype(str):
            status_counts[v] = status_counts.get(v, 0) + 1
    secondary = _share_counts(status_counts)

    sh_counts: dict[str, int] = {}
    if 'safehouse_id' in df.columns:
        for v in df['safehouse_id'].fillna('Unassigned'):
            sh_counts[str(v)] = sh_counts.get(str(v), 0) + 1
    top_sh = sorted(sh_counts.items(), key=lambda x: -x[1])[:8]
    safehouse_rows = [{'safehouseId': k, 'count': v} for k, v in top_sh]

    active = 0
    if 'case_status' in df.columns:
        active = int(df['case_status'].astype(str).str.lower().eq('active').sum())

    summary = {
        'totalResidents': int(len(df)),
        'activeResidents': active,
        'distinctSafehouses': len(sh_counts),
    }

    top_drivers = _read_top_features(features_path, 8)

    model_note = (
        'Multiclass model context from ml-pipelines (current risk level). '
        'Drivers are aggregate feature importances—indicative, not individual predictions.'
        if pipeline_target
        else None
    )
    model_note = _append_live_note(model_note, data_source)

    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': summary,
        'chartRows': chart_rows,
        'secondaryChartRows': secondary,
        'safehouseRows': safehouse_rows,
        'topDrivers': top_drivers,
        'pipelineTarget': pipeline_target,
        'modelNote': model_note,
        'businessQuestion': None,
        'modelQuality': None,
    }


def build_education_section(root: Path, art: Path) -> dict[str, Any]:
    schema_path = art / 'education_records_model_schema.json'
    features_path = art / 'education_records_top_features.csv'

    df, data_source, load_warning = _load_education_frame(root)

    if data_source == 'missing-file':
        return _empty_education_section('missing-file', load_warning)

    if data_source in ('error', 'database-error') and df.empty:
        return _empty_education_section(data_source, load_warning)

    if df.empty:
        return _empty_education_section(data_source if data_source in ('database', 'csv') else 'empty', load_warning)

    pipeline_target = None
    if schema_path.is_file():
        try:
            schema = json.loads(schema_path.read_text(encoding='utf-8'))
            pipeline_target = schema.get('target')
        except Exception:
            pass

    comp_counts: dict[str, int] = {}
    if 'completion_status' in df.columns:
        for v in df['completion_status'].fillna('Unknown').astype(str):
            comp_counts[v] = comp_counts.get(v, 0) + 1
    chart_rows = _share_counts(comp_counts)

    att = prog = None
    if 'attendance_rate' in df.columns:
        s = pd.to_numeric(df['attendance_rate'], errors='coerce').dropna()
        if len(s):
            att = round(float(s.mean()), 2)
    if 'progress_percent' in df.columns:
        s2 = pd.to_numeric(df['progress_percent'], errors='coerce').dropna()
        if len(s2):
            prog = round(float(s2.mean()), 2)

    uniq_r = 0
    if 'resident_id' in df.columns:
        uniq_r = int(df['resident_id'].nunique())

    summary = {
        'totalRecords': int(len(df)),
        'uniqueResidents': uniq_r,
        'avgAttendancePercent': att,
        'avgProgressPercent': prog,
    }

    top_drivers = _read_top_features(features_path, 8)

    model_note = (
        'Progress and completion patterns from the education records pipeline. '
        'Top drivers are notebook feature importances.'
        if pipeline_target
        else None
    )
    model_note = _append_live_note(model_note, data_source)

    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': summary,
        'chartRows': chart_rows,
        'secondaryChartRows': [],
        'safehouseRows': [],
        'topDrivers': top_drivers,
        'pipelineTarget': pipeline_target,
        'modelNote': model_note,
        'businessQuestion': None,
        'modelQuality': None,
    }


def _bool_share(series: pd.Series) -> float | None:
    if series.empty:
        return None
    s = series.astype(str).str.lower().isin(('true', '1', 'yes', 't'))
    return round(float(s.mean()), 4)


def build_health_section(root: Path, art: Path) -> dict[str, Any]:
    schema_path = art / 'health_wellbeing_model_schema.json'
    features_path = art / 'health_wellbeing_top_features.csv'

    df, data_source, load_warning = _load_health_frame(root)

    if data_source == 'missing-file':
        return _empty_health_section('missing-file', load_warning)

    if data_source in ('error', 'database-error') and df.empty:
        return _empty_health_section(data_source, load_warning)

    if df.empty:
        return _empty_health_section(data_source if data_source in ('database', 'csv') else 'empty', load_warning)

    ghs = pd.to_numeric(df['general_health_score'], errors='coerce') if 'general_health_score' in df.columns else pd.Series(dtype=float)
    ghs_clean = ghs.dropna()

    mean_s = med_s = None
    if len(ghs_clean):
        mean_s = round(float(ghs_clean.mean()), 3)
        med_s = round(float(ghs_clean.median()), 3)

    medical = _bool_share(df['medical_checkup_done']) if 'medical_checkup_done' in df.columns else None
    dental = _bool_share(df['dental_checkup_done']) if 'dental_checkup_done' in df.columns else None
    psych = _bool_share(df['psychological_checkup_done']) if 'psychological_checkup_done' in df.columns else None

    nu = 0
    if 'resident_id' in df.columns:
        nu = int(df['resident_id'].nunique())

    nut = sleep = energy = None
    for col, name in (
        ('nutrition_score', 'avgNutritionScore'),
        ('sleep_quality_score', 'avgSleepQualityScore'),
        ('energy_level_score', 'avgEnergyLevelScore'),
    ):
        if col in df.columns:
            s = pd.to_numeric(df[col], errors='coerce').dropna()
            val = round(float(s.mean()), 3) if len(s) else None
            if name == 'avgNutritionScore':
                nut = val
            elif name == 'avgSleepQualityScore':
                sleep = val
            else:
                energy = val

    model_quality: dict[str, Any] | None = None
    business_q = None
    pipeline_target = None
    if schema_path.is_file():
        try:
            schema = json.loads(schema_path.read_text(encoding='utf-8'))
            pipeline_target = schema.get('target')
            business_q = schema.get('business_question')
            mblock = schema.get('metrics') or {}
            sel = schema.get('selected_model') or 'RandomForest'
            metrics = mblock.get(sel) or mblock.get('RandomForest')
            if isinstance(metrics, dict):
                model_quality = {
                    'selectedModel': sel,
                    'holdoutMae': metrics.get('MAE'),
                    'holdoutRmse': metrics.get('RMSE'),
                    'holdoutR2': metrics.get('R2'),
                }
        except Exception:
            pass

    top_drivers = _read_top_features(features_path, 8)

    model_note = (
        'Regression on general health score (notebook RandomForest holdout metrics where available). '
        'Scores are operational indicators, not clinical diagnoses.'
        if pipeline_target
        else None
    )
    model_note = _append_live_note(model_note, data_source)

    summary = {
        'totalRecords': int(len(df)),
        'uniqueResidents': nu,
        'avgGeneralHealthScore': mean_s,
        'medianGeneralHealthScore': med_s,
        'avgNutritionScore': nut,
        'avgSleepQualityScore': sleep,
        'avgEnergyLevelScore': energy,
        'medicalCheckupShare': medical,
        'dentalCheckupShare': dental,
        'psychologicalCheckupShare': psych,
    }

    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': summary,
        'chartRows': [],
        'secondaryChartRows': [],
        'safehouseRows': [],
        'topDrivers': top_drivers,
        'pipelineTarget': pipeline_target,
        'modelNote': model_note,
        'businessQuestion': business_q,
        'modelQuality': model_quality,
    }


def _derive_safehouse_fallback(
    residents_df: pd.DataFrame,
    education_df: pd.DataFrame,
    health_df: pd.DataFrame,
) -> pd.DataFrame:
    if residents_df.empty:
        return pd.DataFrame()

    base = residents_df[['resident_id', 'safehouse_id', 'case_status']].copy()
    base['safehouse_id'] = base['safehouse_id'].fillna('Unassigned').astype(str)
    active_counts = (
        base[base['case_status'].astype(str).str.lower().eq('active')]
        .groupby('safehouse_id', as_index=False)['resident_id']
        .count()
        .rename(columns={'resident_id': 'active_residents'})
    )

    edu = pd.DataFrame(columns=['safehouse_id', 'avg_education_progress'])
    if not education_df.empty and 'resident_id' in education_df.columns and 'progress_percent' in education_df.columns:
        edu_join = education_df[['resident_id', 'progress_percent']].merge(
            base[['resident_id', 'safehouse_id']], on='resident_id', how='left'
        )
        edu_join['progress_percent'] = pd.to_numeric(edu_join['progress_percent'], errors='coerce')
        edu = (
            edu_join.groupby('safehouse_id', as_index=False)['progress_percent']
            .mean()
            .rename(columns={'progress_percent': 'avg_education_progress'})
        )

    health = pd.DataFrame(columns=['safehouse_id', 'avg_health_score'])
    if not health_df.empty and 'resident_id' in health_df.columns and 'general_health_score' in health_df.columns:
        h_join = health_df[['resident_id', 'general_health_score']].merge(
            base[['resident_id', 'safehouse_id']], on='resident_id', how='left'
        )
        h_join['general_health_score'] = pd.to_numeric(h_join['general_health_score'], errors='coerce')
        health = (
            h_join.groupby('safehouse_id', as_index=False)['general_health_score']
            .mean()
            .rename(columns={'general_health_score': 'avg_health_score'})
        )

    out = active_counts.merge(edu, on='safehouse_id', how='left').merge(health, on='safehouse_id', how='left')
    out['month_start'] = datetime.now(timezone.utc).date().replace(day=1).isoformat()
    out['process_recording_count'] = 0
    out['home_visitation_count'] = 0
    out['incident_count'] = 0
    return out


def build_safehouse_performance_section(
    root: Path,
    residents_df: pd.DataFrame,
    education_df: pd.DataFrame,
    health_df: pd.DataFrame,
) -> dict[str, Any]:
    df, data_source, load_warning = _load_safehouse_metrics_frame(root)
    if df.empty:
        fallback = _derive_safehouse_fallback(residents_df, education_df, health_df)
        if fallback.empty:
            return _empty_safehouse_performance_section(data_source if data_source != 'missing-file' else 'empty', load_warning)
        df = fallback
        data_source = 'derived-db-fallback'
        load_warning = (load_warning + ' ' if load_warning else '') + 'Using derived fallback from resident/education/health tables.'

    if 'month_start' in df.columns:
        dts = pd.to_datetime(df['month_start'], errors='coerce')
        if dts.notna().any():
            latest_dt = dts.max()
            df = df.loc[dts == latest_dt].copy()
        else:
            # If pipeline data has no valid month values, keep one most-recent row per safehouse where possible.
            if 'safehouse_id' in df.columns:
                df = df.drop_duplicates(subset=['safehouse_id'], keep='last').copy()

    for col in ('active_residents', 'avg_education_progress', 'avg_health_score'):
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Composite comparison score (simple weighted normalization for dashboard ranking)
    d = df.copy()
    for c in ('active_residents', 'avg_education_progress', 'avg_health_score'):
        mn = float(d[c].min())
        mx = float(d[c].max())
        d[f'{c}_norm'] = 0.0 if abs(mx - mn) < 1e-9 else (d[c] - mn) / (mx - mn)
    d['performance_score'] = (
        d['active_residents_norm'] * 0.30
        + d['avg_education_progress_norm'] * 0.35
        + d['avg_health_score_norm'] * 0.35
    )

    d['safehouse_id'] = d['safehouse_id'].fillna('Unassigned').astype(str)
    rows = []
    for _, r in d.sort_values('performance_score', ascending=False).iterrows():
        rows.append({
            'safehouseId': str(r['safehouse_id']),
            'activeResidents': int(round(float(r['active_residents']))),
            'avgEducationProgress': round(float(r['avg_education_progress']), 2),
            'avgHealthScore': round(float(r['avg_health_score']), 3),
            'performanceScore': round(float(r['performance_score']), 4),
        })

    latest_month = None
    if 'month_start' in d.columns:
        ms = pd.to_datetime(d['month_start'], errors='coerce').dropna()
        if len(ms):
            latest_month = ms.max().strftime('%Y-%m')

    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': {
            'safehouseCount': int(d['safehouse_id'].nunique()),
            'latestMonth': latest_month,
        },
        'rows': rows,
        'topSafehouses': rows[:3],
        'bottomSafehouses': list(reversed(rows[-3:])) if len(rows) >= 3 else rows,
    }


def build_reintegration_section(residents_df: pd.DataFrame, data_source: str, load_warning: str) -> dict[str, Any]:
    if residents_df.empty:
        return _empty_reintegration_section(data_source, load_warning)

    df = residents_df.copy()
    now = datetime.now(timezone.utc)
    window_start = pd.Timestamp(now).tz_localize(None) - pd.DateOffset(months=12)

    if 'date_closed' in df.columns:
        df['date_closed'] = pd.to_datetime(df['date_closed'], errors='coerce')
    else:
        df['date_closed'] = pd.NaT

    closed_mask = df['case_status'].fillna('').astype(str).str.lower().eq('closed')
    completed_mask = (
        df.get('reintegration_status', pd.Series(index=df.index, dtype=str))
        .fillna('')
        .astype(str)
        .str.lower()
        .eq('completed')
    )
    in_window = df['date_closed'].notna() & (df['date_closed'] >= window_start)
    # Denominator: eligible closed/completed cohort in the last 12 months.
    eligible = df[in_window & (closed_mask | completed_mask)].copy()
    # Numerator: completed reintegration among the eligible cohort.
    success = eligible[completed_mask.loc[eligible.index]].copy()

    eligible_count = int(len(eligible))
    success_count = int(len(success))
    success_rate = round(float(success_count / eligible_count), 4) if eligible_count else 0.0

    trend_rows: list[dict[str, Any]] = []
    if not eligible.empty:
        tmp = eligible.copy()
        tmp['_month'] = tmp['date_closed'].dt.to_period('M').astype(str)
        tmp.loc[tmp['_month'].isin(['NaT', 'nan']), '_month'] = 'Unknown'
        for month, grp in tmp.groupby('_month'):
            gcount = int(len(grp))
            gsuccess = int(
                (
                    grp.get('reintegration_status', pd.Series(index=grp.index, dtype=str))
                    .fillna('')
                    .astype(str)
                    .str.lower()
                    .eq('completed')
                ).sum()
            )
            grate = round(float(gsuccess / gcount), 4) if gcount else 0.0
            trend_rows.append({'month': month, 'successCount': gsuccess, 'eligibleCount': gcount, 'successRate': grate})
        trend_rows.sort(key=lambda x: x['month'])

    return {
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': {
            'lookbackMonths': 12,
            'successCount': success_count,
            'eligibleCount': eligible_count,
            'successRate': success_rate,
        },
        'monthlyTrend': trend_rows,
    }


def _ml_service_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def build_tier1_analytics() -> dict[str, Any]:
    """Full payload for GET /reports/tier1-analytics."""
    mls = _ml_service_dir()
    root = _repo_root(mls)
    art = _artifacts(mls)
    residents = build_residents_section(root, art)
    education = build_education_section(root, art)
    health = build_health_section(root, art)
    return {
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'residents': residents,
        'education': education,
        'healthWellbeing': health,
        'safehousePerformance': build_safehouse_performance_section(
            root,
            _load_residents_frame(root)[0],
            _load_education_frame(root)[0],
            _load_health_frame(root)[0],
        ),
        'reintegration': build_reintegration_section(
            _load_residents_frame(root)[0],
            str(residents.get('dataSource') or 'unknown'),
            str(residents.get('loadWarning') or ''),
        ),
    }


def safe_build_tier1_analytics() -> dict[str, Any]:
    try:
        return build_tier1_analytics()
    except Exception as ex:
        return {
            'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
            'residents': _empty_residents_section('error', str(ex)),
            'education': _empty_education_section('error', str(ex)),
            'healthWellbeing': _empty_health_section('error', str(ex)),
            'safehousePerformance': _empty_safehouse_performance_section('error', str(ex)),
            'reintegration': _empty_reintegration_section('error', str(ex)),
        }
