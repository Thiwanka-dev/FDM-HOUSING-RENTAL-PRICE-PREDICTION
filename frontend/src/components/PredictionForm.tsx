import { useState } from 'react'
import type { FormEvent } from 'react'
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
}

// Square footage is kept as text so that the field can be empty while typing.
type FormValues = Omit<RentalFeatures, 'sqfeet' | 'lat' | 'long'> & { sqfeet: string }

type MapView = { state: string; region: Point | null }

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

export default function PredictionForm({ metadata, busy, onEstimate, onChange }: Props) {
  const [values, setValues] = useState(() => initialValues(metadata))
  // The exact point clicked on the map; null when only a region is chosen.
  const [pin, setPin] = useState<Point | null>(null)
  const [mapView, setMapView] = useState<MapView | null>(null)
  const [outsideMap, setOutsideMap] = useState(false)

  const { sqfeet: sqfeetRange, beds: bedsRange, baths: bathsRange } = metadata.numeric
  const state = metadata.states.find((candidate) => candidate.code === values.state)
  const regions = state?.regions ?? []
  const region = regions.find((candidate) => candidate.name === values.region)

  const sqfeet = Number(values.sqfeet)
  const sqfeetValid = values.sqfeet.trim() !== '' && sqfeet > 0
  const sqfeetUnusual = sqfeetValid && (sqfeet < sqfeetRange.min || sqfeet > sqfeetRange.max)
  const complete = values.state !== '' && values.region !== '' && sqfeetValid

  function update(changes: Partial<FormValues>) {
    setValues((current) => ({ ...current, ...changes }))
    onChange()
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
    return { ...values, sqfeet, ...pin }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (complete) onEstimate(features())
  }

  return (
    <form className="card form" onSubmit={submit}>
      <fieldset>
        <legend>
          <span className="legend-title">
            <Icon name="mapPin" />
            Location
          </span>
        </legend>
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
                : 'Select the location of the property on the map, or type or choose a state and region below.'}
          </p>
        )}
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
    </form>
  )
}
