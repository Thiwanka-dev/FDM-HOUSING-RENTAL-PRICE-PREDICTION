import { useEffect, useState } from 'react'
import { getMetadata, predictPrice } from './api'
import type { Metadata, RentalFeatures } from './api'
import Icon from './components/Icon'
import PredictionForm from './components/PredictionForm'
import ResultCard from './components/ResultCard'
import type { Estimate } from './components/ResultCard'
import './App.css'

export default function App() {
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [result, setResult] = useState<Estimate | null>(null)
  const [resultError, setResultError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getMetadata()
      .then(setMetadata)
      .catch((error: Error) => setLoadError(error.message))
  }, [])

  async function estimate(features: RentalFeatures) {
    setBusy(true)
    setResultError(null)
    try {
      setResult({ features, prediction: await predictPrice(features) })
    } catch (error) {
      setResult(null)
      setResultError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // A result no longer describes the form once an input changes.
  function clearResult() {
    setResult(null)
    setResultError(null)
  }

  return (
    <>
      <header className="hero">
        <div className="hero-inner">
          <span className="hero-icon">
            <Icon name="house" size={30} />
          </span>
          <div>
            <h1>U.S. Rental Price Estimator</h1>
            <p>
              Estimate the monthly rent of a home anywhere in the United States, based on about
              180,000 rental listings.
            </p>
          </div>
        </div>
      </header>

      <div className="page">
        {loadError && <p className="card note error">{loadError}</p>}
        {!loadError && !metadata && <p className="card placeholder">Loading…</p>}

        {metadata && (
          <main>
            <PredictionForm
              metadata={metadata}
              busy={busy}
              onEstimate={estimate}
              onChange={clearResult}
            />
            <ResultCard estimate={result} states={metadata.states} error={resultError} />
          </main>
        )}
      </div>
    </>
  )
}
