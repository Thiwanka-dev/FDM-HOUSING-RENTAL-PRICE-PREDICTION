import { useEffect, useRef } from 'react'
import L from 'leaflet'
import type { Feature } from 'geojson'
import 'leaflet/dist/leaflet.css'
import { STATE_SHAPES } from '../geo'

export interface Point {
  lat: number
  long: number
}

interface Props {
  // Where the pin is drawn, if anywhere.
  pin: Point | null
  // The state whose outline is highlighted ('' for none).
  state: string
  // Where the map should move to. A new object moves the map again.
  view: { state: string; region: Point | null } | null
  onPick: (point: Point) => void
}

// The 48 contiguous states; Alaska and Hawaii are reached by dragging.
const INITIAL_BOUNDS: L.LatLngBoundsExpression = [
  [24.5, -125],
  [49.5, -66.5],
]
const REGION_ZOOM = 9

const PIN_ICON = L.divIcon({
  className: 'map-pin',
  html: '<svg viewBox="0 0 24 24" width="34" height="34"><path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/></svg>',
  iconSize: [34, 34],
  // The tip of the pin, at the bottom centre, marks the location.
  iconAnchor: [17, 33],
})

function shapeLayer(code: string): L.GeoJSON {
  return L.geoJSON({ type: 'Feature', properties: {}, geometry: STATE_SHAPES[code] } as Feature, {
    style: { className: 'map-state' },
    interactive: false,
  })
}

export default function MapPicker({ pin, state, view, onPick }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const marker = useRef<L.Marker | null>(null)
  const outline = useRef<L.GeoJSON | null>(null)
  // The click handler is registered once, so it reads the latest callback here.
  const pick = useRef(onPick)

  useEffect(() => {
    pick.current = onPick
  }, [onPick])

  useEffect(() => {
    const created = L.map(container.current!, {
      scrollWheelZoom: false,
      // Half steps let the country fill a narrow map instead of leaving wide margins.
      zoomSnap: 0.5,
    })
    created.fitBounds(INITIAL_BOUNDS)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(created)

    created.on('click', (event) => {
      // Scrolling the page must not zoom the map until the user works with it.
      created.scrollWheelZoom.enable()
      pick.current({ lat: event.latlng.lat, long: event.latlng.lng })
    })
    created.on('mouseout', () => created.scrollWheelZoom.disable())

    map.current = created
    return () => {
      created.remove()
      map.current = null
      marker.current = null
      outline.current = null
    }
  }, [])

  useEffect(() => {
    marker.current?.remove()
    marker.current = pin
      ? L.marker([pin.lat, pin.long], { icon: PIN_ICON, interactive: false }).addTo(map.current!)
      : null
  }, [pin])

  useEffect(() => {
    outline.current?.remove()
    outline.current = state ? shapeLayer(state).addTo(map.current!) : null
  }, [state])

  useEffect(() => {
    if (!view) return
    if (view.region) {
      map.current!.setView([view.region.lat, view.region.long], REGION_ZOOM)
    } else {
      map.current!.fitBounds(shapeLayer(view.state).getBounds())
    }
  }, [view])

  return <div ref={container} className="map" aria-label="Map of the United States" />
}
