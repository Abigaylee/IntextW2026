import { useEffect, useState } from 'react'
import { fetchJson, type AuthMe } from '../api/client'
import { Link } from 'react-router-dom'

type Summary = {
  count: number
  totalEstimated: number
  lastDonationDate?: string
  daysSinceLastDonation?: number | null
}

export function DonorDashboard() {
  const [me, setMe] = useState<AuthMe | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [monthlyAmount, setMonthlyAmount] = useState(25)
  const [recurringEnabled, setRecurringEnabled] = useState(false)

  useEffect(() => {
    fetchJson<AuthMe>('/api/auth/me')
      .then(setMe)
      .catch(() => setErr('Could not load session'))
  }, [])

  useEffect(() => {
    if (!me?.isAuthenticated || !me.roles.includes('Donor')) return
    fetchJson<Summary>('/api/donor/summary')
      .then(setSummary)
      .catch((e: Error) => setErr(e.message))
  }, [me])

  return (
    <div>
      <div className="lh-dash-header">
        <div>
          <h1 className="lh-dash-title h3 mb-1">Your giving</h1>
          <p className="lh-dash-sub mb-0">Track donations, insights, and engagement — styled like the donor dashboard reference.</p>
        </div>
        <div className="d-flex flex-wrap align-items-center gap-2">
          <span className="lh-search-pill small text-secondary d-none d-md-inline">&#128269; Search…</span>
          <span className="rounded-circle bg-primary text-white d-inline-flex align-items-center justify-content-center" style={{ width: 36, height: 36, fontSize: '0.75rem' }}>
            DN
          </span>
        </div>
      </div>

      {err ? <div className="alert alert-warning">{err}</div> : null}

      <p className="text-secondary small mb-3">
        Signed in as <strong>{me?.name ?? '…'}</strong> ·{' '}
        <Link to="/Donor/History">History</Link> · <Link to="/Donor/Insights">Insights</Link>
      </p>

      <div className="lh-kpi-row">
        <div className="lh-kpi-card lh-kpi-deep">
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="small opacity-90">Total estimated (PHP)</div>
              <div className="lh-kpi-value mt-1">{summary ? summary.totalEstimated.toFixed(0) : '—'}</div>
              <div className="lh-kpi-meta mt-1">From linked supporter record</div>
            </div>
            <span className="fs-4">&#36;</span>
          </div>
        </div>
        <div className="lh-kpi-card">
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="text-secondary small">Gifts recorded</div>
              <div className="lh-kpi-value text-dark mt-1">{summary?.count ?? '—'}</div>
              <div className="lh-kpi-meta text-success small mt-1">All time</div>
            </div>
            <span className="text-primary fs-4">&#9829;</span>
          </div>
        </div>
        <div className="lh-kpi-card">
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="text-secondary small">Days since last gift</div>
              <div className="lh-kpi-value text-dark mt-1">{summary?.daysSinceLastDonation ?? '—'}</div>
              <div className="lh-kpi-meta text-warning small mt-1">Recency signal</div>
            </div>
            <span className="text-secondary fs-4">&#9201;</span>
          </div>
        </div>
        <div className="lh-kpi-card lh-kpi-success">
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="small opacity-90">Engagement score</div>
              <div className="lh-kpi-value mt-1">—</div>
              <div className="lh-kpi-meta mt-1">See Insights tab</div>
            </div>
            <span className="fs-4">&#128200;</span>
          </div>
        </div>
      </div>

      <div className="row g-3 mt-1">
        <div className="col-lg-7">
          <div className="lh-chart-card h-100">
            <div className="fw-semibold mb-2">Set up recurring monthly donation</div>
            <p className="text-secondary small mb-3">Choose a monthly amount and save your recurring preference.</p>
            <div className="row g-3 align-items-end">
              <div className="col-sm-6">
                <label className="form-label small text-secondary mb-1" htmlFor="monthlyAmount">
                  Monthly amount (PHP)
                </label>
                <input
                  id="monthlyAmount"
                  className="form-control"
                  type="number"
                  min={1}
                  value={monthlyAmount}
                  onChange={(e) => setMonthlyAmount(Number(e.target.value || 0))}
                />
              </div>
              <div className="col-sm-6">
                <button type="button" className="btn btn-primary lh-btn-pill w-100" onClick={() => setRecurringEnabled(true)}>
                  Save monthly donation
                </button>
              </div>
            </div>
            {recurringEnabled ? <div className="alert alert-success mt-3 mb-0 py-2">Monthly giving set to PHP {monthlyAmount.toLocaleString()}.</div> : null}
          </div>
        </div>
        <div className="col-lg-5">
          <div className="lh-chart-card h-100">
            <div className="fw-semibold mb-2">Your impact summary</div>
            <p className="small text-secondary mb-1">Estimated total given: <strong>PHP {summary ? summary.totalEstimated.toFixed(0) : '—'}</strong></p>
            <p className="small text-secondary mb-1">Donations made: <strong>{summary?.count ?? '—'}</strong></p>
            <p className="small text-secondary mb-0">Last gift date: <strong>{summary?.lastDonationDate ?? '—'}</strong></p>
          </div>
        </div>
      </div>

      {!summary && me?.isAuthenticated && me.roles.includes('Donor') ? (
        <p className="text-muted small mt-2 mb-0">Link your account to a supporter ID at registration to load personalized totals.</p>
      ) : null}
    </div>
  )
}
