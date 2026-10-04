import { useEffect, useState } from 'react'
import { formatDollars } from '../labels'

const DURATION_MS = 600

interface Props {
  amount: number
}

// Counts up from $0 to the amount when the result appears.
export default function AnimatedPrice({ amount }: Props) {
  const [reducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  const [shown, setShown] = useState(0)

  useEffect(() => {
    if (reducedMotion) return

    let frame = 0
    const start = performance.now()
    function step(now: number) {
      const progress = Math.min(1, (now - start) / DURATION_MS)
      // Ease out: fast at first, slowing down towards the final amount.
      setShown(amount * (1 - (1 - progress) ** 3))
      if (progress < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [amount, reducedMotion])

  return (
    <p className="price">
      {/* A screen reader gets the final amount, not every step of the count. */}
      <span aria-hidden="true">{formatDollars(reducedMotion ? amount : shown)}</span>
      <span className="visually-hidden">{formatDollars(amount)}</span>
    </p>
  )
}
