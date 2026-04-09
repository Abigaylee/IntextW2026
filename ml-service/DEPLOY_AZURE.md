# Azure Deployment Guide (ML Service + .NET Bridge)

## 1) Deploy Python ML service

From repo root:

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/build_social_media_cache.py
```

Deploy `ml-service` as a separate Azure App Service (Python).

### Required App Settings

- `SOCIAL_MEDIA_CACHE_PATH=artifacts/social_media_analytics_cache.json`
- `SOCIAL_MEDIA_DATASET_PATH=../datasets/social_media_posts.csv` (optional fallback)
- `DONATIONS_DATASET_PATH=../datasets/donations.csv` (optional; defaults under repo root `datasets/donations.csv` when deployed from this layout)
- `DONATIONS_METRICS_PATH=../ml-pipelines/artifacts/donations_model_metrics.csv` (optional; enriches `/donations/analytics` with pipeline holdout metrics when present)
- Tier-1 program analytics (`GET /reports/tier1-analytics`) prefer the **same PostgreSQL** as social media: set `SOCIAL_MEDIA_DB_URL` or `ConnectionStrings__DefaultConnection` on the ML app so it can read `residents`, `education_records`, and `health_wellbeing_records`. On query failure, it falls back to CSVs. Notebook drivers still load from `ml-pipelines/artifacts/*` relative to repo root. If you deploy only the `ml-service` folder without the full repo, set optional CSV paths, for example:
  - `RESIDENTS_DATASET_PATH=../datasets/residents.csv`
  - `EDUCATION_DATASET_PATH=../datasets/education_records.csv`
  - `HEALTH_WELLBEING_DATASET_PATH=../datasets/health_wellbeing_records.csv`

### Startup command (recommended)

```bash
bash /home/site/wwwroot/startup.sh
```

Verify:

- `GET https://<ml-service>.azurewebsites.net/health`
- `GET https://<ml-service>.azurewebsites.net/social-media/analytics`
- `GET https://<ml-service>.azurewebsites.net/reports/tier1-analytics`
- `GET https://<ml-service>.azurewebsites.net/donations/analytics`

### App settings for stable deploy behavior

- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` (keep this true in current setup)
- `SOCIAL_MEDIA_DB_URL=<your PostgreSQL connection string>` (or `ConnectionStrings__DefaultConnection`)
- optional:
  - `GUNICORN_WORKERS=4`
  - `GUNICORN_TIMEOUT=120`

## 2) Configure .NET backend bridge

Set backend App Service settings:

- `SocialMediaMlApi__BaseUrl=https://<ml-service>.azurewebsites.net`
- `SocialMediaMlApi__AnalyticsPath=/social-media/analytics`
- `SocialMediaMlApi__DonationsAnalyticsPath=/donations/analytics` (optional; this is the default)
- `SocialMediaMlApi__ProgramsTier1AnalyticsPath=/reports/tier1-analytics` (optional; this is the default)
- `SocialMediaMlApi__ApiKey=` (optional if you add key auth)

Redeploy backend.

Verify backend endpoint:

- `GET https://<backend>.azurewebsites.net/api/admin/analytics/social-media`
- `GET https://<backend>.azurewebsites.net/api/admin/analytics/donations-ml` (admin session required)
- `GET https://<backend>.azurewebsites.net/api/admin/analytics/programs-tier1` (admin session required)

## 3) Frontend validation

Redeploy frontend and login as admin.

Open:

- `/Admin/SocialMedia`
- `/Admin/Analytics` (Reports & analytics — tier-1 program cards when ml-service paths resolve)

Expected:

- KPI cards populated
- platform donation chart visible
- recommendations list visible
- best posting windows table visible

## 4) Refreshing precomputed analytics

Any time you refresh the notebook outputs:

```bash
cd ml-service
source .venv/bin/activate
python3 scripts/build_social_media_cache.py
```

Then redeploy/restart ML service so new cache is served.

## 5) Safe production checklist (every release)

1. Merge to `main` (workflow deploys `./ml-service`).
2. Wait for GitHub Action success.
3. In App Service, restart once (optional but recommended after endpoint additions).
4. Run smoke checks:

```bash
curl -sS "https://<ml-service>.azurewebsites.net/health"
curl -sS "https://<ml-service>.azurewebsites.net/openapi.json" | jq '.info, .paths | keys'
curl -sS "https://<ml-service>.azurewebsites.net/reports/tier1-analytics" | jq '.generatedAtUtc, .residents.dataSource'
curl -sS "https://<ml-service>.azurewebsites.net/donations/analytics" | jq '.dataSource, .summary, (.channelMix | length), (.giftTypeMix | length)'
```

Expected:
- `/health` returns `status: ok` and a `buildId`.
- OpenAPI includes both `/reports/tier1-analytics` and `/donations/analytics`.
- Tier1 endpoint responds with JSON payload.
- Donations endpoint returns `dataSource: "database"` in production (or clear warning if fallback used).

## 6) Kudu diagnostics (if anything drifts)

Open Kudu SSH and run:

```bash
cd /home/site/wwwroot
wc -l app/main.py
grep -n "title='Lighthouse ML API'" app/main.py
grep -n "/reports/tier1-analytics\\|/donations/analytics" app/main.py
bash startup.sh
```

If `bash startup.sh` fails, the error text is the source of truth (missing deps, bad env, etc.).
