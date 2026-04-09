from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

# Import psycopg only when connecting to Postgres (allows cache-only runs on platforms
# without psycopg wheels, e.g. Windows ARM64 without libpq).
from fastapi import FastAPI


@dataclass
class Recommendation:
    platform: str
    priority: str
    reason: str
    recommendedAction: str
    suggestedPostHours: list[str]
    estimatedMonthlyLiftPhp: float


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


def _artifact_root() -> Path:
    return Path(__file__).resolve().parents[1]


load_dotenv(_artifact_root() / '.env', override=False)


def _normalize_connection_value(raw: str) -> str:
    value = raw.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_dotnet_style_conn_str(conn_str: str) -> dict[str, Any]:
    mapping = {
        'host': 'host',
        'server': 'host',
        'port': 'port',
        'database': 'dbname',
        'initial catalog': 'dbname',
        'username': 'user',
        'user id': 'user',
        'userid': 'user',
        'uid': 'user',
        'password': 'password',
    }
    options: dict[str, Any] = {}
    for segment in conn_str.split(';'):
        if '=' not in segment:
            continue
        key, value = segment.split('=', 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            continue
        normalized = mapping.get(key)
        if normalized:
            options[normalized] = value
            continue
        if key == 'ssl mode' and value:
            options['sslmode'] = value.lower()
        elif key == 'trust server certificate' and value.lower() == 'true':
            options['sslmode'] = options.get('sslmode', 'require')
    return options


def _resolve_db_connection_value() -> str:
    direct = _normalize_connection_value(os.getenv('SOCIAL_MEDIA_DB_URL', ''))
    if direct:
        return direct
    return _normalize_connection_value(os.getenv('ConnectionStrings__DefaultConnection', ''))


def _connect_db(conn_value: str):
    import psycopg  # noqa: PLC0415

    if conn_value.startswith('postgres://') or conn_value.startswith('postgresql://'):
        return psycopg.connect(conn_value)
    if ';' in conn_value:
        kwargs = _parse_dotnet_style_conn_str(conn_value)
        return psycopg.connect(**kwargs)
    return psycopg.connect(conn_value)


def _load_from_database(db_url: str) -> pd.DataFrame:
    query = """
        SELECT
            post_id, platform, platform_post_id, post_url, created_at, day_of_week, post_hour, post_type, media_type,
            caption, hashtags, num_hashtags, mentions_count, has_call_to_action, call_to_action_type, content_topic,
            sentiment_tone, caption_length, features_resident_story, campaign_name, is_boosted, boost_budget_php,
            impressions, reach, likes, comments, shares, saves, click_throughs, video_views, engagement_rate,
            profile_visits, donation_referrals, estimated_donation_value_php, follower_count_at_post,
            watch_time_seconds, avg_view_duration_seconds, subscriber_count_at_post, forwards
        FROM social_media_posts
    """
    with _connect_db(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


def _load_cached_or_build() -> dict[str, Any]:
    project_root = _artifact_root().parents[0]
    cache_path = Path(os.getenv('SOCIAL_MEDIA_CACHE_PATH', _artifact_root() / 'artifacts' / 'social_media_analytics_cache.json'))
    dataset_path = Path(os.getenv('SOCIAL_MEDIA_DATASET_PATH', project_root / 'datasets' / 'social_media_posts.csv'))

    db_url = _resolve_db_connection_value()
    data_source = 'empty'
    load_warning = ''

    if db_url:
        try:
            df = _load_from_database(db_url)
            data_source = 'database'
        except Exception as ex:
            df = pd.DataFrame()
            data_source = 'database-error'
            load_warning = f'Database connection/query failed: {ex}'
    elif cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding='utf-8'))
        payload.setdefault('dataSource', 'cache')
        payload.setdefault('loadWarning', '')
        return payload
    elif dataset_path.exists():
        df = pd.read_csv(dataset_path)
        data_source = 'csv'
    else:
        df = pd.DataFrame()

    if df.empty:
        return {
            'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
            'currency': 'PHP',
            'dataSource': data_source,
            'loadWarning': load_warning,
            'summary': {
                'totalPosts': 0,
                'totalDonationReferrals': 0,
                'totalEstimatedDonationValuePhp': 0.0,
                'avgEngagementRate': 0.0,
            },
            'platformRanking': [],
            'recommendations': [],
            'bestPostingWindows': [],
        }

    for col in ['donation_referrals', 'estimated_donation_value_php', 'engagement_rate', 'post_hour']:
        if col not in df.columns:
            df[col] = 0

    summary = {
        'totalPosts': int(len(df)),
        'totalDonationReferrals': int(df['donation_referrals'].fillna(0).sum()),
        'totalEstimatedDonationValuePhp': round(float(df['estimated_donation_value_php'].fillna(0).sum()), 2),
        'avgEngagementRate': round(float(df['engagement_rate'].fillna(0).mean()) if len(df) else 0.0, 4),
    }

    grouped = df.groupby('platform', dropna=False).agg(
        posts=('post_id', 'count'),
        donationReferrals=('donation_referrals', 'sum'),
        estimatedDonationValuePhp=('estimated_donation_value_php', 'sum'),
        avgEngagementRate=('engagement_rate', 'mean'),
    ).reset_index().sort_values('estimatedDonationValuePhp', ascending=False)

    total_value = max(float(grouped['estimatedDonationValuePhp'].sum()), 1.0)
    platform_ranking: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        platform_ranking.append({
            'platform': str(row['platform']) if pd.notna(row['platform']) else 'Unknown',
            'posts': _safe_int(row['posts']),
            'donationReferrals': _safe_int(row['donationReferrals']),
            'estimatedDonationValuePhp': round(_safe_float(row['estimatedDonationValuePhp']), 2),
            'avgEngagementRate': round(_safe_float(row['avgEngagementRate']), 4),
            'shareOfDonationValue': round(_safe_float(row['estimatedDonationValuePhp']) / total_value, 4),
        })

    recommendations: list[dict[str, Any]] = []
    if platform_ranking:
        value_series = [p['estimatedDonationValuePhp'] for p in platform_ranking]
        median_value = pd.Series(value_series).median() if value_series else 0
        for item in platform_ranking[:5]:
            priority = 'High' if item['estimatedDonationValuePhp'] >= median_value else 'Medium'
            lift = round(item['estimatedDonationValuePhp'] * (0.2 if priority == 'High' else 0.1), 2)
            platform_df = df[df['platform'] == item['platform']]
            top_hours = (
                platform_df.groupby('post_hour')['estimated_donation_value_php'].mean().sort_values(ascending=False).head(3).index.tolist()
                if len(platform_df) else []
            )
            recommendations.append(Recommendation(
                platform=item['platform'],
                priority=priority,
                reason='Strong donation contribution relative to other platforms.',
                recommendedAction='Post more CTA-led impact stories and appeals on this platform.',
                suggestedPostHours=[str(int(h)) for h in top_hours if pd.notna(h)],
                estimatedMonthlyLiftPhp=lift,
            ).__dict__)

    best_windows = (
        df.groupby(['platform', 'day_of_week', 'post_hour'], dropna=False)
        .agg(avgDonationValuePhp=('estimated_donation_value_php', 'mean'), avgReferrals=('donation_referrals', 'mean'))
        .reset_index()
        .sort_values('avgDonationValuePhp', ascending=False)
        .head(12)
    )
    best_posting_windows: list[dict[str, Any]] = []
    for _, row in best_windows.iterrows():
        best_posting_windows.append({
            'platform': str(row['platform']) if pd.notna(row['platform']) else 'Unknown',
            'dayOfWeek': str(row['day_of_week']) if pd.notna(row['day_of_week']) else 'Unknown',
            'postHour': _safe_int(row['post_hour']),
            'avgDonationValuePhp': round(_safe_float(row['avgDonationValuePhp']), 2),
            'avgReferrals': round(_safe_float(row['avgReferrals']), 2),
        })

    payload = {
        'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
        'currency': 'PHP',
        'dataSource': data_source,
        'loadWarning': load_warning,
        'summary': summary,
        'platformRanking': platform_ranking,
        'recommendations': recommendations,
        'bestPostingWindows': best_posting_windows,
    }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


def _normalize_impact_pipeline_payload(p: dict[str, Any]) -> dict[str, Any]:
    p.setdefault('generatedAtUtc', datetime.now(timezone.utc).isoformat())
    p.setdefault('pipelineName', 'public_impact_snapshots_pipeline')
    p.setdefault('dataSource', 'cache')
    p.setdefault('headline', '')
    p.setdefault('summary', '')
    p.setdefault('metricHighlights', {})
    p.setdefault('loadWarning', '')
    p.setdefault('relatedPipelines', [])
    return p


def _load_impact_pipeline() -> dict[str, Any]:
    """Overlay for Impact page: aligns with ml-pipelines/public_impact_snapshots_pipeline.ipynb."""
    root = _artifact_root()
    cache_path = Path(os.getenv('IMPACT_PIPELINE_CACHE_PATH', root / 'artifacts' / 'impact_pipeline_cache.json'))
    repo_root = root.parent
    sample_path = repo_root / 'artifacts' / 'public_impact_snapshots_sample_payload.json'

    if cache_path.exists():
        data = json.loads(cache_path.read_text(encoding='utf-8'))
        return _normalize_impact_pipeline_payload(data)

    if sample_path.exists():
        sample = json.loads(sample_path.read_text(encoding='utf-8'))
        return _normalize_impact_pipeline_payload(
            {
                'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
                'pipelineName': 'public_impact_snapshots_pipeline',
                'dataSource': 'sample_payload',
                'headline': 'Pipeline-aligned impact indicators',
                'summary': (
                    'Illustrative metrics from the public impact snapshots sample; '
                    'place impact_pipeline_cache.json under ml-service/artifacts/ or set IMPACT_PIPELINE_CACHE_PATH.'
                ),
                'metricHighlights': sample,
                'loadWarning': '',
                'relatedPipelines': [
                    'public_impact_snapshots_pipeline',
                    'donations.ipynb',
                    'residents.ipynb',
                    'safehouse_monthly_metrics_pipeline.ipynb',
                ],
            }
        )

    return _normalize_impact_pipeline_payload(
        {
            'generatedAtUtc': datetime.now(timezone.utc).isoformat(),
            'pipelineName': 'public_impact_snapshots_pipeline',
            'dataSource': 'empty',
            'headline': '',
            'summary': '',
            'metricHighlights': {},
            'loadWarning': 'No impact cache or repo artifacts sample found.',
            'relatedPipelines': [],
        }
    )


app = FastAPI(title='Lighthouse ML API (Social + Impact)', version='1.0.0')
_cache = _load_cached_or_build()
_impact_pipeline_cache = _load_impact_pipeline()


@app.get('/')
def root() -> dict[str, Any]:
    """FastAPI has no HTML home by default; this avoids a bare 404 on GET /."""
    return {
        'service': 'Lighthouse ML API (Social + Impact)',
        'docs': '/docs',
        'health': '/health',
        'socialMediaAnalytics': '/social-media/analytics',
        'impactAnalytics': '/impact/analytics',
    }


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/social-media/summary')
def social_media_summary() -> dict[str, Any]:
    return _cache['summary']


@app.get('/social-media/platform-ranking')
def social_media_platform_ranking() -> list[dict[str, Any]]:
    return _cache['platformRanking']


@app.get('/social-media/recommendations')
def social_media_recommendations() -> list[dict[str, Any]]:
    return _cache['recommendations']


@app.get('/social-media/analytics')
def social_media_analytics() -> dict[str, Any]:
    return _cache


@app.get('/impact/analytics')
def impact_analytics() -> dict[str, Any]:
    """Public impact / snapshot pipeline overlay consumed by Lighthouse GET /api/impact."""
    return _impact_pipeline_cache
