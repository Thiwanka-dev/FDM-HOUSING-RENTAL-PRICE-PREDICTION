import { useEffect, useState } from 'react'
import { getMetadata, predictPrice } from './api'
import type { Metadata, RentalFeatures } from './api'
import Backdrop from './components/Backdrop'
import PredictionForm from './components/PredictionForm'
import ResultCard from './components/ResultCard'
import MarketInsights from './components/MarketInsights'
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
      <Backdrop />
      <div className="shell">
        <header className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <h1>Price every rental with confidence</h1>
              <p>
                Get a data-informed monthly rent estimate, compare the property to similar rental
                listings, and make clearer pricing decisions.
              </p>
              <a className="hero-cta" href="#estimate">
                Get an estimate <span aria-hidden="true">›</span>
              </a>
            </div>
            <div className="hero-image" role="img" aria-label="Modern rental home" />
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
                resultPanel={
                  <ResultCard estimate={result} states={metadata.states} error={resultError} />
                }
              />
              <MarketInsights estimate={result} states={metadata.states} />
            </main>
          )}
        </div>
      </div>
    </>
  )
}
