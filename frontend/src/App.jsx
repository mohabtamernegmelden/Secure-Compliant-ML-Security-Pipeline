import { useEffect, useMemo, useState } from 'react';

const defaultFeatureConfig = {
  numerical_features: ['step', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest'],
  categorical_features: ['type'],
  categories: { type: ['PAYMENT', 'CASH_IN', 'CASH_OUT', 'DEBIT', 'TRANSFER'] },
};

const initialValues = {
  step: 1,
  type: 'TRANSFER',
  amount: 2500.0,
  oldbalanceOrg: 5000.0,
  newbalanceOrig: 2500.0,
  oldbalanceDest: 1000.0,
  newbalanceDest: 3500.0,
};

function App() {
  const [formValues, setFormValues] = useState(initialValues);
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState({ status: 'checking', model_loaded: false });
  const [loading, setLoading] = useState(false);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const riskLabel = useMemo(() => {
    if (!result?.prediction && result?.prediction !== 0) return 'Unknown';
    const label = String(result.prediction).toUpperCase();
    if (label.includes('LEGIT') || label === '0' || label === 'FALSE') return 'LEGITIMATE';
    return 'FRAUD';
  }, [result]);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/health`);
        const payload = await response.json();
        setHealth(payload);
      } catch {
        setHealth({ status: 'offline', model_loaded: false });
      }
    };

    fetchHealth();
    const interval = window.setInterval(fetchHealth, 10000);
    return () => window.clearInterval(interval);
  }, [apiBaseUrl]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormValues((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(formValues).map(([key, value]) => [key, Number.isNaN(Number(value)) ? value : Number(value)])
      );
      const response = await fetch(`${apiBaseUrl}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      // Attempt to parse JSON; if server returned HTML or plain text (e.g., 500 page), fall back to text
      const text = await response.text();
      try {
        const json = JSON.parse(text);
        setResult(json);
      } catch (err) {
        setResult({ error: text });
      }
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="banking-shell">
        <header className="bank-header">
          <div>
            <p className="eyebrow">Northstar Bank • Secure Payments</p>
            <h1>Fraud monitoring center</h1>
            <p className="subtitle">Review suspicious transfers in real time with AI-assisted protection.</p>
          </div>
          <div className={`health-pill ${health.status === 'healthy' ? 'healthy' : health.status === 'offline' ? 'offline' : 'degraded'}`}>
            <span className="dot" />
            {health.status}
          </div>
        </header>

        <section className="overview-grid">
          <article className="overview-card primary">
            <div className="card-label">Available balance</div>
            <div className="card-value">$84,320.00</div>
            <div className="card-meta">Protected by 24/7 fraud monitoring</div>
          </article>
          <article className="overview-card">
            <div className="card-label">Recent alerts</div>
            <div className="card-value">3</div>
            <div className="card-meta">2 require review</div>
          </article>
          <article className="overview-card">
            <div className="card-label">Model status</div>
            <div className="card-value">XGBoost</div>
            <div className="card-meta">Active • {health.model_loaded ? 'ready' : 'warming up'}</div>
          </article>
        </section>

        <section className="content-grid">
          <form onSubmit={handleSubmit} className="panel form-panel">
            <div className="panel-header">
              <div>
                <p className="panel-eyebrow">Transaction review</p>
                <h2>Evaluate a transfer</h2>
              </div>
              <button type="submit" disabled={loading}>{loading ? 'Analyzing…' : 'Run protection check'}</button>
            </div>

            <div className="form-grid">
              {defaultFeatureConfig.numerical_features.map((feature) => (
                <label className="field" key={feature}>
                  <span>{feature}</span>
                  <input type="number" name={feature} value={formValues[feature] ?? ''} onChange={handleChange} />
                </label>
              ))}

              {defaultFeatureConfig.categorical_features.map((feature) => (
                <label className="field" key={feature}>
                  <span>{feature}</span>
                  <select name={feature} value={formValues[feature] ?? ''} onChange={handleChange}>
                    {(defaultFeatureConfig.categories?.[feature] || []).map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </form>

          <aside className="panel result-panel">
            <div className="panel-header">
              <div>
                <p className="panel-eyebrow">Decision</p>
                <h2>Fraud assessment</h2>
              </div>
              <div className={`risk-badge ${riskLabel.toLowerCase() === 'fraud' ? 'fraud' : riskLabel.toLowerCase() === 'legitimate' ? 'legit' : 'unknown'}`}>
                {riskLabel}
              </div>
            </div>

            {result ? (
              <div className="result-body">
                <div className="result-row"><span>Prediction</span><strong>{result.prediction ?? 'N/A'}</strong></div>
                <div className="result-row"><span>Probability</span><strong>{result.probability != null ? `${(result.probability * 100).toFixed(2)}%` : 'N/A'}</strong></div>
                <div className="result-row"><span>Model</span><strong>{result.model_version ?? 'unknown'}</strong></div>
                <div className="result-row"><span>Latency</span><strong>{result.processing_time_ms != null ? `${result.processing_time_ms.toFixed(1)} ms` : 'N/A'}</strong></div>
                {result.error ? <div className="error-box">{result.error}</div> : null}
              </div>
            ) : (
              <div className="empty-state">
                <p>No review has been run yet.</p>
                <span>Submit a transfer to generate a security decision.</span>
              </div>
            )}
          </aside>
        </section>
      </div>
    </div>
  );
}

export default App;
