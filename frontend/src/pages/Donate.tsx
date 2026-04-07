import { useMemo, useState } from 'react'

const presetAmounts = [25, 50, 100, 250]

export function Donate() {
  const [selectedAmount, setSelectedAmount] = useState<number | 'custom'>(50)
  const [customAmount, setCustomAmount] = useState('')
  const [cardName, setCardName] = useState('')
  const [cardNumber, setCardNumber] = useState('')
  const [expiry, setExpiry] = useState('')
  const [cvv, setCvv] = useState('')

  const effectiveAmount = useMemo(() => {
    if (selectedAmount === 'custom') {
      return Number.parseFloat(customAmount || '0')
    }
    return selectedAmount
  }, [customAmount, selectedAmount])

  return (
    <section className="mx-auto" style={{ maxWidth: '760px' }}>
      <h1 className="h2 mb-2">Donate</h1>
      <p className="text-secondary mb-4">
        Thank you for supporting Light on a Hill Foundation. Choose an amount and enter your card details below.
      </p>

      <div className="card border-0 shadow-sm">
        <div className="card-body p-4">
          <h2 className="h5 mb-3">Choose Amount</h2>
          <div className="d-flex flex-wrap gap-2 mb-3">
            {presetAmounts.map((amount) => (
              <button
                key={amount}
                type="button"
                className={`btn ${selectedAmount === amount ? 'btn-primary' : 'btn-outline-primary'}`}
                onClick={() => setSelectedAmount(amount)}
              >
                ${amount}
              </button>
            ))}
            <button
              type="button"
              className={`btn ${selectedAmount === 'custom' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setSelectedAmount('custom')}
            >
              Custom
            </button>
          </div>

          {selectedAmount === 'custom' && (
            <div className="mb-4">
              <label htmlFor="customAmount" className="form-label">
                Custom amount
              </label>
              <div className="input-group">
                <span className="input-group-text">$</span>
                <input
                  id="customAmount"
                  className="form-control"
                  type="number"
                  min="1"
                  step="0.01"
                  placeholder="0.00"
                  value={customAmount}
                  onChange={(e) => setCustomAmount(e.target.value)}
                />
              </div>
            </div>
          )}

          <h2 className="h5 mb-3">Card Information</h2>
          <div className="row g-3">
            <div className="col-12">
              <label htmlFor="cardName" className="form-label">
                Name on card
              </label>
              <input
                id="cardName"
                className="form-control"
                type="text"
                placeholder="Jane Smith"
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
              />
            </div>
            <div className="col-12">
              <label htmlFor="cardNumber" className="form-label">
                Card number
              </label>
              <input
                id="cardNumber"
                className="form-control"
                type="text"
                inputMode="numeric"
                placeholder="1234 5678 9012 3456"
                value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value)}
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="expiry" className="form-label">
                Expiry (MM/YY)
              </label>
              <input
                id="expiry"
                className="form-control"
                type="text"
                placeholder="08/28"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="cvv" className="form-label">
                CVV
              </label>
              <input
                id="cvv"
                className="form-control"
                type="password"
                inputMode="numeric"
                placeholder="123"
                value={cvv}
                onChange={(e) => setCvv(e.target.value)}
              />
            </div>
          </div>

          <div className="mt-4 d-flex flex-wrap justify-content-between align-items-center gap-3">
            <strong className="fs-5">Total: ${Number.isFinite(effectiveAmount) ? effectiveAmount.toFixed(2) : '0.00'}</strong>
            <button type="button" className="btn btn-primary lh-btn-pill px-4">
              Donate Now
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
