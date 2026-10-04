import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Metadata, ModelInfo, RentalFeatures } from '../api'
import { AMENITIES, formatDollars, optionLabel, regionLabel } from '../labels'

interface Props {
  metadata: Metadata
  models: ModelInfo[]
  // The request that is in progress, if any.
  busy: 'estimate' | 'compare' | null
  onEstimate: (features: RentalFeatures, model: string) => void
  onCompare: (features: RentalFeatures) => void
  onChange: () => void
}

// Square footage is kept as text so that the field can be empty while typing.
type FormValues = Omit<RentalFeatures, 'sqfeet'> & { sqfeet: string }

function initialValues(metadata: Metadata): FormValues {
  return {
    state: '',
    region: '',
    type: metadata.type[0],
    sqfeet: String(metadata.numeric.sqfeet.default),
    beds: metadata.numeric.beds.default,
    baths: metadata.numeric.baths.default,
    laundry_options: 'Unknown',
    parking_options: 'Unknown',
    cats_allowed: false,
    dogs_allowed: false,
    smoking_allowed: false,
    wheelchair_access: false,
    electric_vehicle_charge: false,
    comes_furnished: false,
  }
}

function steps(min: number, max: number, step: number): number[] {
  const count = Math.round((max - min) / step) + 1
  return Array.from({ length: count }, (_, index) => min + index * step)
}

export default function PredictionForm({
  metadata,
  models,
  busy,
  onEstimate,
  onCompare,
  onChange,
}: Props) {
  const [values, setValues] = useState(() => initialValues(metadata))
  const [modelId, setModelId] = useState(() => models.find((model) => model.default)!.id)
  const model = models.find((candidate) => candidate.id === modelId)!

  const { sqfeet: sqfeetRange, beds: bedsRange, baths: bathsRange } = metadata.numeric
  const regions = metadata.states.find((state) => state.code === values.state)?.regions ?? []

  const sqfeet = Number(values.sqfeet)
  const sqfeetValid = values.sqfeet.trim() !== '' && sqfeet > 0
  const sqfeetUnusual = sqfeetValid && (sqfeet < sqfeetRange.min || sqfeet > sqfeetRange.max)
  const complete = values.state !== '' && values.region !== '' && sqfeetValid

  function update(changes: Partial<FormValues>) {
    setValues((current) => ({ ...current, ...changes }))
    onChange()
  }

  function selectState(code: string) {
    const stateRegions = metadata.states.find((state) => state.code === code)?.regions ?? []
    // A state with a single region needs no second choice.
    update({ state: code, region: stateRegions.length === 1 ? stateRegions[0].name : '' })
  }

  function selectModel(id: string) {
    setModelId(id)
    onChange()
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (complete) onEstimate({ ...values, sqfeet }, modelId)
  }

  return (
    <form className="card form" onSubmit={submit}>
      <fieldset>
        <legend>Location</legend>
        <div className="grid">
          <div className="field">
            <label htmlFor="state">State</label>
            <select
              id="state"
              value={values.state}
              onChange={(event) => selectState(event.target.value)}
            >
              <option value="" disabled>
                Select a state
              </option>
              {metadata.states.map((state) => (
                <option key={state.code} value={state.code}>
                  {state.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="region">Region</label>
            <select
              id="region"
              value={values.region}
              disabled={values.state === ''}
              onChange={(event) => update({ region: event.target.value })}
            >
              <option value="" disabled>
                {values.state === '' ? 'Select a state first' : 'Select a region'}
              </option>
              {regions.map((region) => (
                <option key={region.name} value={region.name}>
                  {regionLabel(region.name)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend>Property</legend>
        <div className="grid">
          <div className="field">
            <label htmlFor="type">Property type</label>
            <select
              id="type"
              value={values.type}
              onChange={(event) => update({ type: event.target.value })}
            >
              {metadata.type.map((type) => (
                <option key={type} value={type}>
                  {optionLabel(type)}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="sqfeet">Size (square feet)</label>
            <input
              id="sqfeet"
              type="number"
              min="1"
              step="any"
              inputMode="decimal"
              value={values.sqfeet}
              onChange={(event) => update({ sqfeet: event.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="beds">Bedrooms</label>
            <select
              id="beds"
              value={values.beds}
              onChange={(event) => update({ beds: Number(event.target.value) })}
            >
              {steps(bedsRange.min, bedsRange.max, 1).map((beds) => (
                <option key={beds} value={beds}>
                  {beds === 0 ? '0 (studio)' : beds}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="baths">Bathrooms</label>
            <select
              id="baths"
              value={values.baths}
              onChange={(event) => update({ baths: Number(event.target.value) })}
            >
              {steps(bathsRange.min, bathsRange.max, 0.5).map((baths) => (
                <option key={baths} value={baths}>
                  {baths}
                </option>
              ))}
            </select>
          </div>
        </div>
        {!sqfeetValid && <p className="note error">Enter a size greater than 0.</p>}
        {sqfeetUnusual && (
          <p className="note warning">
            This size is outside the range of most listings the models were trained on (
            {sqfeetRange.min.toLocaleString()} to {sqfeetRange.max.toLocaleString()} square feet).
            The estimate is less reliable.
          </p>
        )}
      </fieldset>

      <fieldset>
        <legend>Amenities</legend>
        <div className="grid">
          <div className="field">
            <label htmlFor="laundry">Laundry</label>
            <select
              id="laundry"
              value={values.laundry_options}
              onChange={(event) => update({ laundry_options: event.target.value })}
            >
              {metadata.laundry_options.map((option) => (
                <option key={option} value={option}>
                  {optionLabel(option)}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="parking">Parking</label>
            <select
              id="parking"
              value={values.parking_options}
              onChange={(event) => update({ parking_options: event.target.value })}
            >
              {metadata.parking_options.map((option) => (
                <option key={option} value={option}>
                  {optionLabel(option)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="checks">
          {AMENITIES.map(({ field, label }) => (
            <label key={field} className="check">
              <input
                type="checkbox"
                checked={values[field]}
                onChange={(event) => update({ [field]: event.target.checked })}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend>Model</legend>
        <div className="field">
          <label htmlFor="model">Prediction model</label>
          <select id="model" value={modelId} onChange={(event) => selectModel(event.target.value)}>
            {models.map((candidate) => (
              <option key={candidate.id} value={candidate.id} disabled={!candidate.available}>
                {candidate.name}
                {candidate.default && ' (recommended)'}
                {!candidate.available && ' (not installed)'}
              </option>
            ))}
          </select>
        </div>
        {model.test_mae !== null && model.test_r2 !== null && (
          <p className="hint">
            Average test error {formatDollars(model.test_mae)}, R² {model.test_r2.toFixed(2)}.
            {model.default && ' This model had the lowest error of the four.'}
          </p>
        )}
      </fieldset>

      <div className="actions">
        <button type="submit" disabled={!complete || busy !== null}>
          {busy === 'estimate' ? 'Estimating…' : 'Estimate rent'}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={!complete || busy !== null}
          onClick={() => onCompare({ ...values, sqfeet })}
        >
          {busy === 'compare' ? 'Comparing…' : 'Compare all models'}
        </button>
      </div>
    </form>
  )
}
