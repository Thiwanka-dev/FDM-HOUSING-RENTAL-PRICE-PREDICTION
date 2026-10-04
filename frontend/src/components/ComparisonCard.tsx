import type { ModelInfo, Prediction } from '../api'
import { formatDollars } from '../labels'

interface Props {
  models: ModelInfo[]
  predictions: Prediction[]
}

export default function ComparisonCard({ models, predictions }: Props) {
  const prices = predictions.map((prediction) => prediction.price)
  const highest = Math.max(...prices)
  const lowest = Math.min(...prices)
  const recommended = models.find((model) => model.default)

  return (
    <section className="card result" aria-live="polite">
      <h2>Estimated monthly rent by model</h2>

      <ul className="comparison reveal">
        {models.map((model) => {
          const prediction = predictions.find((candidate) => candidate.model === model.id)
          return (
            <li key={model.id}>
              <div className="comparison-heading">
                <span className="comparison-name">
                  {model.name}
                  {model.default && <span className="badge">Recommended</span>}
                </span>
                {prediction && (
                  <span className="comparison-price">{formatDollars(prediction.price)}</span>
                )}
              </div>

              {prediction ? (
                // Every bar starts at $0, so the lengths compare the estimates directly.
                <div className="bar" style={{ width: `${(prediction.price / highest) * 100}%` }} />
              ) : (
                <p className="comparison-detail">
                  Not installed. Run: python -m models.setup_models
                </p>
              )}

              {model.test_mae !== null && model.test_r2 !== null && (
                <p className="comparison-detail">
                  Average test error {formatDollars(model.test_mae)} · R² {model.test_r2.toFixed(2)}
                </p>
              )}
            </li>
          )
        })}
      </ul>

      <p className="accuracy reveal">
        {predictions.length > 1 && (
          <>
            The estimates range from <strong>{formatDollars(lowest)}</strong> to{' '}
            <strong>{formatDollars(highest)}</strong>.{' '}
          </>
        )}
        {recommended &&
          `The ${recommended.name} had the lowest error on listings it had not seen, so its estimate is the recommended one.`}
      </p>
    </section>
  )
}
