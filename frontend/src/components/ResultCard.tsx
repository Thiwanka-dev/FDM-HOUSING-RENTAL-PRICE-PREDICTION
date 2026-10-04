import type { Prediction } from '../api'
import { formatDollars } from '../labels'
import AnimatedPrice from './AnimatedPrice'

interface Props {
  prediction: Prediction | null
  error: string | null
}

export default function ResultCard({ prediction, error }: Props) {
  return (
    <section className="card result" aria-live="polite">
      <h2>Estimated monthly rent</h2>

      {error && <p className="note error">{error}</p>}

      {!error && !prediction && (
        <p className="placeholder">
          Describe the property and select <strong>Estimate rent</strong>.
        </p>
      )}

      {!error && prediction && (
        <div className="reveal">
          <AnimatedPrice amount={prediction.price} />
          <p className="model">Predicted by the {prediction.name} model</p>
          {prediction.test_mae !== null && (
            <p className="accuracy">
              On listings it had not seen, this model was off by{' '}
              <strong>{formatDollars(prediction.test_mae)}</strong> on average. The actual rent can
              differ by more.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
