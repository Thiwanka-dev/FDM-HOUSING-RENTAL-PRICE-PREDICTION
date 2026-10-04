// Display text for the values stored in the dataset.

import type { RentalFeatures } from './api'

const OPTION_LABELS: Record<string, string> = {
  Unknown: 'Not specified',
  'w/d in unit': 'Washer and dryer in unit',
  'w/d hookups': 'Washer and dryer hookups',
  'laundry in bldg': 'Laundry in building',
}

// "seattle-tacoma" -> "Seattle-Tacoma"; existing capitals such as "TX" stay.
function capitaliseWords(text: string): string {
  return text.replace(/(^|[\s\-/])([a-z])/g, (_, before, letter) => before + letter.toUpperCase())
}

export function optionLabel(value: string): string {
  return OPTION_LABELS[value] ?? value.charAt(0).toUpperCase() + value.slice(1)
}

export function regionLabel(value: string): string {
  return capitaliseWords(value)
}

type Amenity = keyof {
  [K in keyof RentalFeatures as RentalFeatures[K] extends boolean ? K : never]: true
}

export const AMENITIES: { field: Amenity; label: string }[] = [
  { field: 'cats_allowed', label: 'Cats allowed' },
  { field: 'dogs_allowed', label: 'Dogs allowed' },
  { field: 'smoking_allowed', label: 'Smoking allowed' },
  { field: 'comes_furnished', label: 'Furnished' },
  { field: 'wheelchair_access', label: 'Wheelchair access' },
  { field: 'electric_vehicle_charge', label: 'Electric vehicle charging' },
]

const dollars = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

export function formatDollars(amount: number): string {
  return dollars.format(amount)
}
