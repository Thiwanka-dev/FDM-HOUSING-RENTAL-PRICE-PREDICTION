import type { State } from '../api'
import { regionLabel } from '../labels'
import type { Estimate } from './ResultCard'

interface Props {
  estimate: Estimate | null
  states: State[]
}

export default function MarketInsights({ estimate, states }: Props) {
  const state = estimate
    ? states.find((candidate) => candidate.code === estimate.features.state)
    : null
  const location = estimate
    ? `${regionLabel(estimate.features.region)}, ${state?.name ?? estimate.features.state}`
    : 'Rental markets across the United States'

  return (
    <section className="market-insights" aria-labelledby="market-insights-title">
      <div className="insights-intro">
        <h2 id="market-insights-title">Market context</h2>
        <p>See the data foundation used to place each home in its local rental context.</p>
        <div className="listing-count">
          <strong>179,599</strong>
          <span>cleaned rental listings</span>
        </div>
      </div>

      <div className="insights-photo" role="img" aria-label="Homes in a residential neighbourhood" />

      <div className="insights-location">
        <p className="insights-place">{location}</p>
        <p>
          Each estimate considers the property location together with its size, type, rooms, and
          amenities.
        </p>
        <div className="signal-bars" aria-hidden="true">
          <span style={{ height: '42%' }} />
          <span style={{ height: '68%' }} />
          <span style={{ height: '55%' }} />
          <span style={{ height: '86%' }} />
          <span style={{ height: '72%' }} />
          <span style={{ height: '100%' }} />
          <span style={{ height: '80%' }} />
        </div>
        <p className="signal-label">Location · property · amenities</p>
      </div>
    </section>
  )
}
