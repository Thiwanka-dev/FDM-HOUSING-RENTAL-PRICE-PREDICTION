import { useEffect, useState } from 'react'

// Photos in public/backgrounds; see CREDITS.md there for their sources.
const PHOTOS = [1, 2, 3, 4, 5, 6].map((number) => `/backgrounds/home-${number}.jpg`)
const SECONDS_PER_PHOTO = 7

// Full-page photos of homes behind the content, changing every few seconds.
export default function Backdrop() {
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    // People who ask for less motion keep the first photo.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const timer = setInterval(
      () => setCurrent((index) => (index + 1) % PHOTOS.length),
      SECONDS_PER_PHOTO * 1000,
    )
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="backdrop" aria-hidden="true">
      {PHOTOS.map((photo, index) => (
        <div
          key={photo}
          className={index === current ? 'backdrop-photo shown' : 'backdrop-photo'}
          style={{ backgroundImage: `url(${photo})` }}
        />
      ))}
    </div>
  )
}
