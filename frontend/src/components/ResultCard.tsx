import type { Prediction, RentalFeatures, State } from '../api'
import { AMENITIES, formatDollars, optionLabel, regionLabel } from '../labels'
import AnimatedPrice from './AnimatedPrice'

export interface Estimate {
  features: RentalFeatures
  prediction: Prediction
}

interface Props {
  estimate: Estimate | null
  states: State[]
  error: string | null
}

function count(amount: number, unit: string): string {
  return `${amount} ${unit}${amount === 1 ? '' : 's'}`
}

// The property the estimate is for, in the user's own terms.
function Summary({ features, states }: { features: RentalFeatures; states: State[] }) {
  const state = states.find((candidate) => candidate.code === features.state)
  const amenities = AMENITIES.filter(({ field }) => features[field]).map(({ label }) => label)

  const details = [
    features.beds === 0 ? 'Studio' : count(features.beds, 'bedroom'),
    count(features.baths, 'bathroom'),
    `${features.sqfeet.toLocaleString()} sq ft`,
  ]
  // "Not specified" says nothing about the property, so it is left out.
  const extras = [features.laundry_options, features.parking_options]
    .filter((option) => option !== 'Unknown')
    .map(optionLabel)
    .concat(amenities)

  return (
    <div className="summary">
      <p className="summary-title">
        {optionLabel(features.type)} in {regionLabel(features.region)}, {state?.name}
      </p>
      <p className="summary-details">{details.join(' · ')}</p>
      {extras.length > 0 && <p className="summary-extras">{extras.join(' · ')}</p>}
    </div>
  )
}

export default function ResultCard({ estimate, states, error }: Props) {
  return (
    <section className="card result" aria-live="polite">
      <h2>Estimated monthly rent</h2>

      {error && <p className="note error">{error}</p>}

      {!error && !estimate && (
        <p className="placeholder">
          Describe the property and select <strong>Estimate rent</strong>.
        </p>
      )}

      {!error && estimate && (
        <div className="reveal">
          <Summary features={estimate.features} states={states} />
          <AnimatedPrice amount={estimate.prediction.price} />
          {estimate.prediction.test_mae !== null && (
            <p className="accuracy">
              This is an estimate. For similar homes, our estimates are about{' '}
              <strong>{formatDollars(estimate.prediction.test_mae)}</strong> above or below the
              actual rent on average.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
