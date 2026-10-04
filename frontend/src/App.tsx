import { useEffect, useState } from 'react'
import { getMetadata, predictPrice } from './api'
import type { Metadata, Prediction, RentalFeatures } from './api'
import PredictionForm from './components/PredictionForm'
import ResultCard from './components/ResultCard'
import './App.css'

export default function App() {
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [predictError, setPredictError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getMetadata()
      .then(setMetadata)
      .catch((error: Error) => setLoadError(error.message))
  }, [])

  async function estimate(features: RentalFeatures) {
    setLoading(true)
    setPredictError(null)
    try {
      setPrediction(await predictPrice(features))
    } catch (error) {
      setPrediction(null)
      setPredictError((error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // An estimate no longer describes the form once an input changes.
  function clearResult() {
    setPrediction(null)
    setPredictError(null)
  }

  return (
    <div className="page">
      <header>
        <h1>U.S. Rental Price Estimator</h1>
        <p>Estimate the monthly rent of a residential property in the United States.</p>
      </header>

      {loadError && <p className="card note error">{loadError}</p>}
      {!loadError && !metadata && <p className="card placeholder">Loading…</p>}

      {metadata && (
        <main>
          <PredictionForm
            metadata={metadata}
            loading={loading}
            onSubmit={estimate}
            onChange={clearResult}
          />
          <ResultCard prediction={prediction} error={predictError} />
        </main>
      )}
    </div>
  )
}
