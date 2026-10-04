import { useEffect, useState } from 'react'
import { comparePrices, getMetadata, getModels, predictPrice } from './api'
import type { Metadata, ModelInfo, Prediction, RentalFeatures } from './api'
import ComparisonCard from './components/ComparisonCard'
import PredictionForm from './components/PredictionForm'
import ResultCard from './components/ResultCard'
import './App.css'

interface Reference {
  metadata: Metadata
  models: ModelInfo[]
}

type Result =
  | { kind: 'estimate'; prediction: Prediction }
  | { kind: 'compare'; predictions: Prediction[] }

export default function App() {
  const [reference, setReference] = useState<Reference | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [resultError, setResultError] = useState<string | null>(null)
  const [busy, setBusy] = useState<Result['kind'] | null>(null)

  useEffect(() => {
    Promise.all([getMetadata(), getModels()])
      .then(([metadata, models]) => setReference({ metadata, models }))
      .catch((error: Error) => setLoadError(error.message))
  }, [])

  async function run(kind: Result['kind'], request: () => Promise<Result>) {
    setBusy(kind)
    setResultError(null)
    try {
      setResult(await request())
    } catch (error) {
      setResult(null)
      setResultError((error as Error).message)
    } finally {
      setBusy(null)
    }
  }

  function estimate(features: RentalFeatures, model: string) {
    run('estimate', async () => ({
      kind: 'estimate',
      prediction: await predictPrice(features, model),
    }))
  }

  function compare(features: RentalFeatures) {
    run('compare', async () => ({
      kind: 'compare',
      predictions: await comparePrices(features),
    }))
  }

  // A result no longer describes the form once an input changes.
  function clearResult() {
    setResult(null)
    setResultError(null)
  }

  return (
    <div className="page">
      <header>
        <h1>U.S. Rental Price Estimator</h1>
        <p>Estimate the monthly rent of a residential property in the United States.</p>
      </header>

      {loadError && <p className="card note error">{loadError}</p>}
      {!loadError && !reference && <p className="card placeholder">Loading…</p>}

      {reference && (
        <main>
          <PredictionForm
            metadata={reference.metadata}
            models={reference.models}
            busy={busy}
            onEstimate={estimate}
            onCompare={compare}
            onChange={clearResult}
          />
          {result?.kind === 'compare' ? (
            <ComparisonCard models={reference.models} predictions={result.predictions} />
          ) : (
            <ResultCard prediction={result?.prediction ?? null} error={resultError} />
          )}
        </main>
      )}
    </div>
  )
}
