import type { ModelInfo } from '../api'
import { FEATURE_IMPORTANCE } from '../data/featureImportance'
import { formatDollars } from '../labels'

interface Props {
  models: ModelInfo[]
}

const DESCRIPTIONS: Record<string, string> = {
  neural_network:
    'A feed-forward network. It learns an embedding for each category, such as the region, and uses periodic features of the coordinates to capture how rent changes with location.',
  random_forest:
    'The average of 200 decision trees, each trained on a different random sample of the listings.',
  gradient_boosting:
    'A sequence of 150 small decision trees, where each tree corrects the errors of the trees before it.',
  linear_ridge:
    'A linear model with L2 regularisation. It is the baseline the other models are compared against.',
}

export default function AboutModels({ models }: Props) {
  const recommended = models.find((model) => model.default)
  const largest = Math.max(...FEATURE_IMPORTANCE.map((row) => row.maeIncrease))

  return (
    <div className="about">
      <section className="card">
        <h2>How the models compare</h2>
        <p className="lead">
          Four models were trained on the same rental listings and scored on a test set of listings
          that none of them had seen.
          {recommended &&
            ` The ${recommended.name} had the lowest error, so it is the default model.`}
        </p>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col" className="number">
                  MAE
                </th>
                <th scope="col" className="number">
                  RMSE
                </th>
                <th scope="col" className="number">
                  R²
                </th>
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <tr key={model.id}>
                  <th scope="row">
                    {model.name}
                    {model.default && <span className="badge">Recommended</span>}
                  </th>
                  <td className="number">
                    {model.test_mae === null ? '–' : formatDollars(model.test_mae)}
                  </td>
                  <td className="number">
                    {model.test_rmse === null ? '–' : formatDollars(model.test_rmse)}
                  </td>
                  <td className="number">
                    {model.test_r2 === null ? '–' : model.test_r2.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <dl className="definitions">
          <div>
            <dt>MAE</dt>
            <dd>
              Mean absolute error: the average difference between the estimate and the actual rent.
              Lower is better.
            </dd>
          </div>
          <div>
            <dt>RMSE</dt>
            <dd>
              Root mean squared error: like MAE, but large mistakes count more. Lower is better.
            </dd>
          </div>
          <div>
            <dt>R²</dt>
            <dd>
              The share of the variation in rent that the model explains, from 0 to 1. Higher is
              better.
            </dd>
          </div>
        </dl>
      </section>

      <section className="card">
        <h2>The four models</h2>
        <dl className="definitions">
          {models.map((model) => (
            <div key={model.id}>
              <dt>{model.name}</dt>
              <dd>{DESCRIPTIONS[model.id]}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h2>What the Neural Network relies on</h2>
        <p className="lead">
          Each bar shows how much the average error grows, in dollars, when the values of one input
          are shuffled between listings. A longer bar means the model depends more on that input.
          Location and size matter most.
        </p>

        <ul className="importance">
          {FEATURE_IMPORTANCE.map((row) => (
            <li key={row.feature}>
              <span className="importance-name">{row.feature}</span>
              <span className="importance-track">
                <span className="bar" style={{ width: `${(row.maeIncrease / largest) * 100}%` }} />
              </span>
              <span className="importance-value">+{formatDollars(row.maeIncrease)}</span>
            </li>
          ))}
        </ul>

        <p className="hint">
          Region, state, latitude and longitude describe the same thing, so their individual values
          are an indication, not an exact measurement.
        </p>
      </section>

      <section className="card">
        <h2>Limits of the estimates</h2>
        <ul className="limits">
          <li>
            An estimate is a typical rent for listings like the one described. An individual
            property can differ by much more than the average error.
          </li>
          <li>
            The location is taken as the typical coordinates of the chosen region, not the exact
            address.
          </li>
          <li>
            The models only know the listings they were trained on. They do not follow changes in
            the rental market after that data was collected.
          </li>
        </ul>
      </section>
    </div>
  )
}
