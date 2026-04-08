# IS 455 Pipeline Backlog (Locked)

This backlog defines distinct business problems and modeling goals for at least 7 complete pipelines.

## 1) Residents Reintegration Readiness
- **Business question:** Which residents are likely to achieve reintegration readiness in the next review window?
- **Predictive target:** readiness score/category at next checkpoint.
- **Explanatory target:** drivers of readiness (program intensity, education progression, incident burden, support continuity).

## 2) Safehouse Operational Risk
- **Business question:** Which safehouses face elevated operational risk next month?
- **Predictive target:** risk flag or incident volume.
- **Explanatory target:** which factors (occupancy strain, staffing coverage, prior incidents) explain risk.

## 3) Donation Allocation Shortfall Risk
- **Business question:** Which allocation requests are likely to be underfunded?
- **Predictive target:** shortfall probability or amount.
- **Explanatory target:** request features and donor behavior patterns that explain shortfalls.

## 4) Intervention Plan Completion Likelihood
- **Business question:** Which intervention plans are at risk of non-completion?
- **Predictive target:** completion probability.
- **Explanatory target:** treatment intensity, partner support, and compliance signals explaining completion.

## 5) Incident Escalation Prediction
- **Business question:** Which reported incidents are likely to escalate and require intensive response?
- **Predictive target:** escalation flag.
- **Explanatory target:** incident context and historical factors associated with escalation.

## 6) Partner Assignment Success
- **Business question:** Which partner-resident assignments are most likely to succeed?
- **Predictive target:** assignment success score.
- **Explanatory target:** partner profile and case attributes explaining success odds.

## 7) Education Outcome Progress
- **Business question:** Which residents are likely to fall behind in education outcomes?
- **Predictive target:** progress risk flag.
- **Explanatory target:** attendance, intervention support, and baseline preparedness effects.

## 8) Health and Wellbeing Risk Stratification
- **Business question:** Which residents are at highest near-term wellbeing risk?
- **Predictive target:** risk category/score.
- **Explanatory target:** stressors, counseling continuity, and medical indicators explaining risk.

## 9) Social Media Donation Lift
- **Business question:** Which post and campaign features are associated with higher estimated donation value?
- **Predictive target:** `estimated_donation_value_php`.
- **Explanatory target:** content topics, channel, campaign effects.

## 10) Counseling Session Concerns
- **Business question:** Which session patterns predict flagged concerns for follow-up?
- **Predictive target:** `concerns_flagged`.
- **Explanatory target:** session type, duration, emotional state signals.

## 11) Home Visitation Follow-Up Need
- **Business question:** Which visits require follow-up action?
- **Predictive target:** `follow_up_needed`.
- **Explanatory target:** cooperation, safety, location, family presence.

## Full execution checklist
See [ALL_PIPELINES_ROADMAP.md](ALL_PIPELINES_ROADMAP.md) for registry keys, notebook mapping, and tier B (optional) datasets.

## Deployment Priority (Top 3)
1. Residents Reintegration Readiness
2. Donation Allocation Shortfall Risk
3. Safehouse Operational Risk
