import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import type { Metadata, RentalFeatures } from '../api'
import Combobox from './Combobox'
import Icon from './Icon'
import MapPicker from './MapPicker'
import type { Point } from './MapPicker'
import { locate } from '../geo'
import { AMENITIES, optionLabel, regionLabel } from '../labels'

interface Props {
  metadata: Metadata
  // An estimate is being requested.
  busy: boolean
  onEstimate: (features: RentalFeatures) => void
  onChange: () => void
  resultPanel: ReactNode
}

// Numeric inputs are kept as text so that fields can be empty while typing.
type FormValues = Omit<RentalFeatures, 'sqfeet' | 'beds' | 'baths' | 'lat' | 'long'> & {
  sqfeet: string
  beds: string
  baths: string
}

type MapView = { state: string; region: Point | null }

function initialValues(metadata: Metadata): FormValues {
  return {
    state: '',
    region: '',
    type: metadata.type[0],
    sqfeet: String(metadata.numeric.sqfeet.default),
    beds: String(metadata.numeric.beds.default),
    baths: String(metadata.numeric.baths.default),
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

export default function PredictionForm({
  metadata,
  busy,
  onEstimate,
  onChange,
  resultPanel,
}: Props) {
  const [values, setValues] = useState(() => initialValues(metadata))
  // The exact point clicked on the map; null when only a region is chosen.
  const [pin, setPin] = useState<Point | null>(null)
  const [mapView, setMapView] = useState<MapView | null>(null)
  const [outsideMap, setOutsideMap] = useState(false)

  const { sqfeet: sqfeetRange } = metadata.numeric
  const state = metadata.states.find((candidate) => candidate.code === values.state)
  const regions = state?.regions ?? []
  const region = regions.find((candidate) => candidate.name === values.region)

  const sqfeet = Number(values.sqfeet)
  const sqfeetValid = values.sqfeet.trim() !== '' && sqfeet > 0
  const sqfeetUnusual = sqfeetValid && (sqfeet < sqfeetRange.min || sqfeet > sqfeetRange.max)
  const beds = Number(values.beds)
  const baths = Number(values.baths)
  const bedsValid = /^\d+$/.test(values.beds) && beds >= 0 && beds <= 8
  const bathsValid = /^\d+$/.test(values.baths) && baths >= 0 && baths <= 8
  const complete =
    values.state !== '' && values.region !== '' && sqfeetValid && bedsValid && bathsValid

  function update(changes: Partial<FormValues>) {
    setValues((current) => ({ ...current, ...changes }))
    onChange()
  }

  function updateInteger(field: 'beds' | 'baths', value: string) {
    // Ignore letters, signs, decimal points, and other non-integer characters.
    if (/^\d*$/.test(value)) update({ [field]: value })
  }

  const stateOptions = metadata.states.map((item) => ({
    value: item.code,
    label: item.name,
    keyword: item.code,
  }))
  // Before a state is chosen, every region can be searched, so each is listed
  // with its state. The value holds both, because region names repeat.
  const regionOptions = (state ? [state] : metadata.states).flatMap((item) =>
    item.regions.map((option) => ({
      value: `${item.code}|${option.name}`,
      label: state ? regionLabel(option.name) : `${regionLabel(option.name)}, ${item.name}`,
    })),
  )

  function selectState(code: string) {
    const stateRegions = metadata.states.find((item) => item.code === code)?.regions ?? []
    // A state with a single region needs no second choice.
    const only = stateRegions.length === 1 ? stateRegions[0] : null
    update({ state: code, region: only?.name ?? '' })
    setPin(null)
    setOutsideMap(false)
    setMapView(code === '' ? null : { state: code, region: only })
  }

  function selectRegion(key: string) {
    setPin(null)
    setOutsideMap(false)
    if (key === '') {
      update({ region: '' })
      return
    }
    const [code, name] = key.split('|')
    const chosen = metadata.states
      .find((item) => item.code === code)!
      .regions.find((item) => item.name === name)!
    update({ state: code, region: name })
    setMapView({ state: code, region: chosen })
  }

  // A click on the map sets the coordinates and fills in the state and region.
  function pickOnMap(point: Point) {
    const location = locate(metadata.states, point.lat, point.long)
    setOutsideMap(location === null)
    if (location === null) return
    update(location)
    setPin({ lat: Number(point.lat.toFixed(4)), long: Number(point.long.toFixed(4)) })
  }

  function features(): RentalFeatures {
    return { ...values, sqfeet, beds, baths, ...pin }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (complete) onEstimate(features())
  }

  return (
    <form id="estimate" className="estimator-card" onSubmit={submit}>
      <h2 className="estimate-title">Get an estimate</h2>
      <div className="estimator-workspace">
        <div className="form-fields">
      <fieldset>
        <legend>
          <span className="legend-title">
            <Icon name="mapPin" />
            Location
          </span>
        </legend>
        <div className="grid">
          <div className="field">
            <label htmlFor="state">State</label>
            <Combobox
              id="state"
              options={stateOptions}
              value={values.state}
              onChange={selectState}
              noun="state"
              placeholder="Type or choose a state"
            />
          </div>
          <div className="field">
            <label htmlFor="region">Region</label>
            <Combobox
              id="region"
              options={regionOptions}
              value={values.region === '' ? '' : `${values.state}|${values.region}`}
              onChange={selectRegion}
              noun="region"
              placeholder="Type or choose a region"
            />
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend>
          <span className="legend-title">
            <Icon name="house" />
            Property
          </span>
        </legend>
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
            <input
              id="beds"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              required
              value={values.beds}
              aria-invalid={!bedsValid}
              aria-describedby={!bedsValid ? 'beds-error' : undefined}
              onChange={(event) => updateInteger('beds', event.target.value)}
            />
            {!bedsValid && (
              <p id="beds-error" className="field-error" role="alert">
                Enter a whole number from 0 to 8.
              </p>
            )}
          </div>
          <div className="field">
            <label htmlFor="baths">Bathrooms</label>
            <input
              id="baths"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              required
              value={values.baths}
              aria-invalid={!bathsValid}
              aria-describedby={!bathsValid ? 'baths-error' : undefined}
              onChange={(event) => updateInteger('baths', event.target.value)}
            />
            {!bathsValid && (
              <p id="baths-error" className="field-error" role="alert">
                Enter a whole number from 0 to 8.
              </p>
            )}
          </div>
        </div>
        {!sqfeetValid && <p className="note error">Enter a size greater than 0.</p>}
        {sqfeetUnusual && (
          <p className="note warning">
            This size is outside the range of most listings we have seen (
            {sqfeetRange.min.toLocaleString()} to {sqfeetRange.max.toLocaleString()} square feet).
            The estimate is less reliable.
          </p>
        )}
      </fieldset>

      <fieldset>
        <legend>
          <span className="legend-title">
            <Icon name="sparkles" />
            Amenities
          </span>
        </legend>
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
        <div className="chips">
          {AMENITIES.map(({ field, label, icon }) => (
            // The checkbox is hidden; the whole chip shows whether it is selected.
            <label key={field} className="chip">
              <input
                type="checkbox"
                className="visually-hidden"
                checked={values[field]}
                onChange={(event) => update({ [field]: event.target.checked })}
              />
              <Icon name={icon} size={16} />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <button type="submit" disabled={!complete || busy}>
        {busy ? 'Estimating…' : 'Estimate rent'}
      </button>
        </div>

        <div className="estimate-visuals">
          <section className="map-panel" aria-label="Choose the property location">
            <MapPicker
              pin={pin ?? region ?? null}
              state={values.state}
              view={mapView}
              onPick={pickOnMap}
            />
            {outsideMap ? (
              <p className="note error">
                That point is outside the areas we cover. Select a point in the United States.
              </p>
            ) : (
              <p className="hint map-hint">
                {pin && region && state
                  ? `Pin at ${pin.lat.toFixed(4)}, ${pin.long.toFixed(4)}, in ${regionLabel(region.name)}, ${state.name}.`
                  : region
                    ? `Using the typical location of ${regionLabel(region.name)}. Select a point on the map for the exact location.`
                    : 'Select the location on the map, or choose a state and region.'}
              </p>
            )}
          </section>
          {resultPanel}
        </div>
      </div>
    </form>
  )
}
