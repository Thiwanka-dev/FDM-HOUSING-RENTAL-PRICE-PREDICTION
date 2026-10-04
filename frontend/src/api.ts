// Types and calls of the backend API (see backend/app/main.py).

export interface Region {
  name: string
  lat: number
  long: number
}

export interface State {
  code: string
  name: string
  regions: Region[]
}

export interface NumericRange {
  min: number
  max: number
  default: number
}

export interface Metadata {
  states: State[]
  type: string[]
  laundry_options: string[]
  parking_options: string[]
  numeric: {
    sqfeet: NumericRange
    beds: NumericRange
    baths: NumericRange
  }
}

export interface RentalFeatures {
  region: string
  state: string
  type: string
  sqfeet: number
  beds: number
  baths: number
  laundry_options: string
  parking_options: string
  cats_allowed: boolean
  dogs_allowed: boolean
  smoking_allowed: boolean
  wheelchair_access: boolean
  electric_vehicle_charge: boolean
  comes_furnished: boolean
  // Exact location chosen on the map. Without it, the backend uses the
  // typical coordinates of the region.
  lat?: number
  long?: number
}

export interface Prediction {
  model: string
  name: string
  price: number
  test_mae: number | null
}

export interface ModelInfo {
  id: string
  name: string
  default: boolean
  available: boolean
  test_mae: number | null
  test_rmse: number | null
  test_r2: number | null
}

const OFFLINE_MESSAGE =
  'The backend is not running. Start it with: uvicorn backend.app.main:app --reload'

// FastAPI reports an error either as a sentence or as a list of field errors.
function errorMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => `${item.loc?.at(-1) ?? 'input'}: ${item.msg}`)
      .join('; ')
  }
  return 'The request failed.'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new Error(OFFLINE_MESSAGE)
  }

  // The development server answers 500 when it cannot reach the backend.
  const isJson = response.headers.get('content-type')?.includes('application/json')
  if (!isJson) throw new Error(OFFLINE_MESSAGE)

  const body = await response.json()
  if (!response.ok) throw new Error(errorMessage(body.detail))
  return body as T
}

export function getMetadata(): Promise<Metadata> {
  return request('/api/metadata')
}

export function getModels(): Promise<ModelInfo[]> {
  return request('/api/models')
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function predictPrice(features: RentalFeatures, model: string): Promise<Prediction> {
  return post('/api/predict', { features, model })
}

// One prediction from every model whose saved file is available.
export function comparePrices(features: RentalFeatures): Promise<Prediction[]> {
  return post('/api/predict/compare', { features })
}
