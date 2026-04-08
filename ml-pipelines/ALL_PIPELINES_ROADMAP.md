# IS 455 — Complete roadmap for all pipelines

Use this file as your **master checklist**. Finish pipelines **one at a time** (fully written + runnable) before moving on—quality beats partial work everywhere.

## How each pipeline maps to the rubric

For **every** pipeline you submit, the notebook must tell one story with these parts:

| Section | What to include |
|--------|-------------------|
| **1. Problem framing** | Business question, stakeholder, **predictive vs explanatory** goals, success metrics. |
| **2. Data, prep, exploration** | Load from `datasets/`, document cleaning/joins, show exploration (missingness, tables, plots). |
| **3. Modeling & feature selection** | Interpretable model + predictive model; justify features. |
| **4. Evaluation** | Proper split/CV, right metrics, **business interpretation**, FP/FN costs. |
| **5. Causal / relationships** | Drivers, correlation vs causation, limitations, recommendations. |
| **6. Deployment** *(if required)* | How outputs would be used or delivered (even if short). |

**Engine:** `pipeline_kit.py` runs the dual models and writes `artifacts/` when `save_artifacts=True`. **You** still write the narrative in markdown.

---

## Tier A — Registered in `pipeline_kit` (11 pipelines)

Set `PIPELINE_NAME` in `blank_notebook.ipynb` (or call `run_pipeline_by_name("...")`) to match the **Registry key**.

| # | Registry key (`PIPELINE_NAME`) | Primary notebook to own the story | Dataset CSV | What the kit models (target) |
|---|-------------------------------|-------------------------------------|---------------|-------------------------------|
| 1 | `residents` | `residents.ipynb` | `residents.csv` | `current_risk_level` (classification) |
| 2 | `safehouses` | `safehouses.ipynb` | `safehouses.csv` | Occupancy / capacity (regression) |
| 3 | `donation_allocations` | `donation_allocations.ipynb` | `donation_allocations.csv` | `amount_allocated` (regression) |
| 4 | `intervention_plans` | `intervention_plans.ipynb` | `intervention_plans.csv` | Plan `status` (classification) |
| 5 | `incident_reports` | `incident_reports.ipynb` | `incident_reports.csv` | `severity` ordinal (regression) |
| 6 | `partner_assignments` | `partner_assignments.ipynb` | `partner_assignments.csv` | `status` (classification) |
| 7 | `education_records` | `education_records.ipynb` | `education_records.csv` | `completion_status` (classification) |
| 8 | `health_wellbeing_records` | `health_wellbeing_records.ipynb` | `health_wellbeing_records.csv` | Mean wellbeing scores (regression) |
| 9 | `social_media_posts` | `social_media_posts_pipeline.ipynb` | `social_media_posts.csv` | `estimated_donation_value_php` (regression) |
| 10 | `process_recordings` | `process_recordings.ipynb` | `process_recordings.csv` | `concerns_flagged` (classification) |
| 11 | `home_visitations` | `home_visitations.ipynb` | `home_visitations.csv` | `follow_up_needed` (classification) |

**Batch run:** open `run_all_pipelines.ipynb` and run all cells to refresh metrics/artifacts for every Tier A pipeline.

---

## Tier B — Extra notebooks (not in `pipeline_kit` yet)

These use other CSVs. Either:

- **Option A:** Extend `pipeline_kit.py` with a new `prepare_*` + registry key (best for consistency), or  
- **Option B:** Copy the pattern from `blank_notebook.ipynb` and hand-roll prep for that CSV only.

| Notebook | Dataset(s) | Suggested business angle |
|----------|------------|---------------------------|
| `donations.ipynb` | `donations.csv` | Donation amount / recurring behavior |
| `in_kind_donation_items.ipynb` | `in_kind_donation_items.csv` | In-kind value / category |
| `supporters_pipeline.ipynb` | `supporters.csv` | Retention / engagement segments |
| `partners.ipynb` | `partners.csv` | Partner capacity / coverage |
| `public_impact_snapshots_pipeline.ipynb` | `public_impact_snapshots.csv` | Impact narrative vs metrics |
| `safehouse_monthly_metrics_pipeline.ipynb` | `safehouse_monthly_metrics.csv` | Trends / forecasting |

Treat Tier B as **optional depth** after Tier A is solid.

---

## Suggested order of work (all Tier A)

1. **residents** — richest case story; use to nail your rubric prose pattern.  
2. **education_records** or **health_wellbeing_records** — clear outcomes.  
3. **donation_allocations** — donor/program bridge.  
4. **intervention_plans** + **incident_reports** — operations/risk.  
5. **safehouses** + **partner_assignments** — capacity/partners.  
6. **social_media_posts** + **process_recordings** + **home_visitations** — outreach + clinical notes + field visits.

---

## Definition of done (per pipeline)

- [ ] `Kernel → Restart & Run All` succeeds with cwd = `ml-pipelines/`.  
- [ ] Every rubric section has **your words**, not only code.  
- [ ] Predictive and explanatory goals are **explicit** and match the models you show.  
- [ ] At least one **exploration** artifact (table or plot) supports your prep choices.  
- [ ] Evaluation names **false positives / false negatives** in org terms.  
- [ ] Causal section states **limitations** clearly.

---

## Files to lean on

- `pipeline_kit.py` — shared modeling + artifacts.  
- `blank_notebook.ipynb` — template + `PIPELINE_NAME` driver.  
- `run_all_pipelines.ipynb` — run everything once.  
- `pipeline_backlog.md` — original business-problem blurbs (items 1–8).  

When all Tier A boxes feel “done,” you have **11 complete pipeline stories** aligned with the course lifecycle.
