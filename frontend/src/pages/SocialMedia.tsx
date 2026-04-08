import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchJson } from '../api/client'

type SocialMediaSummary = {
  totalPosts: number
  totalDonationReferrals: number
  totalEstimatedDonationValuePhp: number
  avgEngagementRate: number
}

type PlatformRankingRow = {
  platform: string
  posts: number
  donationReferrals: number
  estimatedDonationValuePhp: number
  avgEngagementRate: number
  shareOfDonationValue: number
}

type RecommendationRow = {
  platform: string
  priority: string
  reason: string
  recommendedAction: string
  suggestedPostHours: string[]
  estimatedMonthlyLiftPhp: number
}

type PostingWindowRow = {
  platform: string
  dayOfWeek: string
  postHour: number
  avgDonationValuePhp: number
  avgReferrals: number
}

type SocialMediaAnalyticsResponse = {
  generatedAtUtc: string
  currency: string
  summary: SocialMediaSummary
  platformRanking: PlatformRankingRow[]
  recommendations: RecommendationRow[]
  bestPostingWindows: PostingWindowRow[]
}

export function SocialMedia() {
  const [data, setData] = useState<SocialMediaAnalyticsResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    fetchJson<SocialMediaAnalyticsResponse>('/api/admin/analytics/social-media')
      .then(setData)
      .catch((e: Error) => setErr(e.message))
  }, [])

  const platformChart = useMemo(
    () => (data?.platformRanking ?? []).slice(0, 6).map((r) => ({ platform: r.platform, value: Math.round(r.estimatedDonationValuePhp) })),
    [data],
  )

  return (
    <div>
      <h1 className="h3 mb-2">Social Media Analytics</h1>
      <p className="text-secondary mb-3">
        Pipeline-backed insights showing which platforms are driving donations and where to focus posting effort.
      </p>
      {err ? <div className="alert alert-warning">{err}</div> : null}

      <div className="row g-3 mb-3">
        <div className="col-md-3">
          <div className="card border-0 shadow-sm h-100"><div className="card-body"><div className="small text-secondary">Total posts</div><div className="h4 mb-0">{data?.summary.totalPosts ?? '—'}</div></div></div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm h-100"><div className="card-body"><div className="small text-secondary">Donation referrals</div><div className="h4 mb-0">{data?.summary.totalDonationReferrals?.toLocaleString() ?? '—'}</div></div></div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm h-100"><div className="card-body"><div className="small text-secondary">Estimated donation value (PHP)</div><div className="h4 mb-0">{data ? Math.round(data.summary.totalEstimatedDonationValuePhp).toLocaleString() : '—'}</div></div></div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm h-100"><div className="card-body"><div className="small text-secondary">Average engagement rate</div><div className="h4 mb-0">{data ? `${(data.summary.avgEngagementRate * 100).toFixed(2)}%` : '—'}</div></div></div>
        </div>
      </div>

      <div className="row g-3 mb-3">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-body">
              <h2 className="h5">Platforms leading donation value</h2>
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={platformChart}>
                    <XAxis dataKey="platform" tick={{ fontSize: 11 }} />
                    <YAxis />
                    <Tooltip formatter={(v) => `PHP ${Number(v ?? 0).toLocaleString()}`} />
                    <Bar dataKey="value" fill="var(--bs-primary)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-body">
              <h2 className="h5">Where to post more</h2>
              <div className="vstack gap-2">
                {(data?.recommendations ?? []).slice(0, 4).map((r) => (
                  <div key={`${r.platform}-${r.priority}`} className="border rounded p-2">
                    <div className="d-flex justify-content-between align-items-center">
                      <strong>{r.platform}</strong>
                      <span className={`badge ${r.priority === 'High' ? 'text-bg-success' : 'text-bg-secondary'}`}>{r.priority}</span>
                    </div>
                    <div className="small text-secondary mt-1">{r.reason}</div>
                    <div className="small mt-1"><strong>Action:</strong> {r.recommendedAction}</div>
                    <div className="small mt-1"><strong>Best hours:</strong> {r.suggestedPostHours.join(', ') || '—'}</div>
                    <div className="small mt-1"><strong>Estimated lift:</strong> PHP {Math.round(r.estimatedMonthlyLiftPhp).toLocaleString()}</div>
                  </div>
                ))}
                {(data?.recommendations?.length ?? 0) === 0 ? <p className="small text-secondary mb-0">No recommendations yet.</p> : null}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm">
        <div className="card-body">
          <h2 className="h5">Best posting windows by platform</h2>
          <div className="table-responsive">
            <table className="table table-sm mb-0">
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>Day</th>
                  <th>Hour</th>
                  <th>Avg donation value (PHP)</th>
                  <th>Avg referrals</th>
                </tr>
              </thead>
              <tbody>
                {(data?.bestPostingWindows ?? []).slice(0, 20).map((w, idx) => (
                  <tr key={`${w.platform}-${w.dayOfWeek}-${w.postHour}-${idx}`}>
                    <td>{w.platform}</td>
                    <td>{w.dayOfWeek}</td>
                    <td>{w.postHour}:00</td>
                    <td>{Math.round(w.avgDonationValuePhp).toLocaleString()}</td>
                    <td>{w.avgReferrals.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(data?.bestPostingWindows?.length ?? 0) === 0 ? <p className="small text-secondary mt-2 mb-0">No posting-window analytics yet.</p> : null}
          <p className="small text-secondary mt-3 mb-0">Generated: {data?.generatedAtUtc ? new Date(data.generatedAtUtc).toLocaleString() : '—'}</p>
        </div>
      </div>
    </div>
  )
}
