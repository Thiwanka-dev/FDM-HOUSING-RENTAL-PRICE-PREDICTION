import { useEffect, useState } from 'react'
import { comparePrices, getMetadata, getModels, predictPrice } from './api'
import type { Metadata, ModelInfo, Prediction, RentalFeatures } from './api'
import AboutModels from './components/AboutModels'
import ComparisonCard from './components/ComparisonCard'
import PredictionForm from './components/PredictionForm'
import ResultCard from './components/ResultCard'
import './App.css'

interface Reference {
  metadata: Metadata
  models: ModelInfo[]
}

const PAGES = [
  { id: 'estimate', label: 'Estimate rent' },
  { id: 'about', label: 'About the models' },
] as const

type Page = (typeof PAGES)[number]['id']

type Result =
  | { kind: 'estimate'; prediction: Prediction }
  | { kind: 'compare'; predictions: Prediction[] }

export default function App() {
  const [reference, setReference] = useState<Reference | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [resultError, setResultError] = useState<string | null>(null)
  const [busy, setBusy] = useState<Result['kind'] | null>(null)
  const [page, setPage] = useState<Page>('estimate')

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

      <nav aria-label="Pages">
        {PAGES.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className="tab"
            aria-current={page === id ? 'page' : undefined}
            onClick={() => setPage(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {loadError && <p className="card note error">{loadError}</p>}
      {!loadError && !reference && <p className="card placeholder">Loading…</p>}

      {reference && (
        <>
          {/* Hidden, not removed, so the form keeps its values between pages. */}
          <main hidden={page !== 'estimate'}>
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
          {page === 'about' && <AboutModels models={reference.models} />}
        </>
      )}

      <footer>IT3051 Fundamentals of Data Mining project.</footer>
    </div>
  )
}
