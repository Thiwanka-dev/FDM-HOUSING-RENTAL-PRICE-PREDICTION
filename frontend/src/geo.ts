// Turns a point on the map into the state and region the models expect.
//
// usStates.json holds simplified state boundaries, taken from the Leaflet
// choropleth tutorial (leafletjs.com/examples/choropleth), which derives them
// from U.S. Census Bureau data. Positions are [longitude, latitude].

import type { State } from './api'
import boundaries from './data/usStates.json'

type Ring = number[][]

export interface StateShape {
  type: string
  // A Polygon is a list of rings; a MultiPolygon is a list of polygons.
  coordinates: Ring[] | Ring[][]
}

export const STATE_SHAPES = boundaries as Record<string, StateShape>

export interface MapLocation {
  state: string
  region: string
}

// The boundaries are coarse, so a point on the coast or an island can fall
// outside every state. Such a point is accepted when a region is this close.
const MAX_DISTANCE_OUTSIDE_KM = 40

function polygons(shape: StateShape): Ring[][] {
  return shape.type === 'Polygon' ? [shape.coordinates as Ring[]] : (shape.coordinates as Ring[][])
}

// Ray casting: a point is inside when a ray from it crosses the edges an odd
// number of times.
function contains(shape: StateShape, lat: number, long: number): boolean {
  let inside = false
  for (const polygon of polygons(shape)) {
    for (const ring of polygon) {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i]
        const [xj, yj] = ring[j]
        if (yi > lat !== yj > lat && long < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
          inside = !inside
        }
      }
    }
  }
  return inside
}

// Great-circle distance between two points (haversine formula).
function distanceKm(lat1: number, long1: number, lat2: number, long2: number): number {
  const radians = Math.PI / 180
  const a =
    Math.sin(((lat2 - lat1) * radians) / 2) ** 2 +
    Math.cos(lat1 * radians) *
      Math.cos(lat2 * radians) *
      Math.sin(((long2 - long1) * radians) / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(a))
}

function nearestRegion(states: State[], lat: number, long: number) {
  let best: (MapLocation & { distance: number }) | null = null
  for (const state of states) {
    for (const region of state.regions) {
      const distance = distanceKm(lat, long, region.lat, region.long)
      if (best === null || distance < best.distance) {
        best = { state: state.code, region: region.name, distance }
      }
    }
  }
  return best
}

// The state that contains the point and the nearest region of that state.
// Returns null for a point outside the United States.
export function locate(states: State[], lat: number, long: number): MapLocation | null {
  const containing = states.find(
    (state) => STATE_SHAPES[state.code] && contains(STATE_SHAPES[state.code], lat, long),
  )
  const nearest = nearestRegion(containing ? [containing] : states, lat, long)

  if (nearest === null) return null
  if (!containing && nearest.distance > MAX_DISTANCE_OUTSIDE_KM) return null
  return { state: nearest.state, region: nearest.region }
}
