import { useCallback, useLayoutEffect, useRef, type RefObject } from 'react'

const NEAR_BOTTOM_PX = 48

export function useStickToBottom<T extends HTMLElement>(): {
  ref: RefObject<T>
  onScroll: () => void
} {
  const ref = useRef<T>(null)
  // A ref, not state: scroll events must not trigger re-renders.
  const pinnedRef = useRef(true)

  const onScroll = useCallback(() => {
    const el = ref.current
    if (!el) return
    pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_PX
  }, [])

  // No dependency array: any re-render of the owner may have grown the content, so a
  // fixed list would silently miss a growth source. Layout effect: scroll before paint,
  // so streamed text never flashes below the fold for a frame.
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    if (pinnedRef.current) {
      // Intentionally instant (no animation): mid-animation scroll events would wrongly
      // unpin during streaming, and instant scrolling respects reduced-motion users.
      el.scrollTop = el.scrollHeight
    }
  })

  return { ref, onScroll }
}
