import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

export interface Option {
  value: string
  label: string
  // An extra word that also finds the option, such as a state's code.
  keyword?: string
}

interface Props {
  id: string
  options: Option[]
  // The selected option's value, or '' when nothing is selected.
  value: string
  onChange: (value: string) => void
  // What one option is called in messages, for example "state".
  noun: string
  placeholder: string
}

// Options that fit the typed text; those that start with it come first.
function search(options: Option[], text: string): Option[] {
  const query = text.trim().toLowerCase()
  if (query === '') return options

  const starts: Option[] = []
  const contains: Option[] = []
  for (const option of options) {
    const label = option.label.toLowerCase()
    if (label.startsWith(query) || option.keyword?.toLowerCase() === query) starts.push(option)
    else if (label.includes(query)) contains.push(option)
  }
  return [...starts, ...contains]
}

// The single option the typed text stands for, if there is exactly one.
function resolve(options: Option[], text: string): Option | null {
  const query = text.trim().toLowerCase()
  const exact = options.filter(
    (option) => option.label.toLowerCase() === query || option.keyword?.toLowerCase() === query,
  )
  if (exact.length === 1) return exact[0]

  const matches = search(options, text)
  return matches.length === 1 ? matches[0] : null
}

// A text field with a list: the user can type a name or choose one.
export default function Combobox({ id, options, value, onChange, noun, placeholder }: Props) {
  // The text being typed. It is dropped when the selection changes from
  // outside, for example by a click on the map.
  const [draft, setDraft] = useState<{ text: string; forValue: string } | null>(null)
  const [open, setOpen] = useState(false)
  // Set by the arrow button: list every option, whatever text is in the field.
  const [showAll, setShowAll] = useState(false)
  const [focused, setFocused] = useState(false)
  const [active, setActive] = useState(0)
  const list = useRef<HTMLUListElement>(null)

  const typed = draft !== null && draft.forValue === value ? draft.text : null
  const selected = options.find((option) => option.value === value)
  const text = typed ?? selected?.label ?? ''
  // Opening the list without typing shows every option.
  const visible = typed === null || showAll ? options : search(options, typed)

  // Text that was left in the field without matching exactly one option.
  let error: string | null = null
  if (typed !== null && typed.trim() !== '' && !focused) {
    error =
      search(options, typed).length === 0
        ? `No ${noun} matches “${typed.trim()}”. Check the spelling or choose one from the list.`
        : `More than one ${noun} matches “${typed.trim()}”. Type more of the name or choose one from the list.`
  }

  useEffect(() => {
    if (open) list.current?.children[active]?.scrollIntoView({ block: 'nearest' })
  }, [open, active])

  function choose(option: Option) {
    setDraft(null)
    setOpen(false)
    if (option.value !== value) onChange(option.value)
  }

  function type(newText: string) {
    setDraft({ text: newText, forValue: value })
    setShowAll(false)
    setOpen(true)
    setActive(0)
  }

  // Leaving the field: accept the text if it identifies one option.
  function settle() {
    setFocused(false)
    setOpen(false)
    if (typed === null) return

    const match = resolve(options, typed)
    if (match) {
      choose(match)
    } else {
      // Nothing valid is selected any more; the text stays so it can be corrected.
      setDraft({ text: typed, forValue: '' })
      if (value !== '') onChange('')
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (!open) {
        setOpen(true)
        setActive(0)
      } else if (visible.length > 0) {
        const step = event.key === 'ArrowDown' ? 1 : -1
        setActive((active + step + visible.length) % visible.length)
      }
    } else if (event.key === 'Enter' && open) {
      // Enter chooses from the list instead of submitting the form.
      event.preventDefault()
      const option = visible[active] ?? (typed !== null ? resolve(options, typed) : null)
      if (option) choose(option)
    } else if (event.key === 'Escape' && open) {
      setOpen(false)
      setDraft(null)
    }
  }

  return (
    <div className="combobox">
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        value={text}
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={open && visible[active] ? `${id}-option-${active}` : undefined}
        aria-invalid={error !== null}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(event) => type(event.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={settle}
        onKeyDown={onKeyDown}
      />
      <button
        type="button"
        className="combobox-toggle"
        tabIndex={-1}
        aria-label={`Show all ${noun}s`}
        // Keeps the focus in the text field, so the list is not closed by a blur.
        onMouseDown={(event) => event.preventDefault()}
        onClick={(event) => {
          setOpen(!open)
          setShowAll(true)
          setActive(Math.max(0, options.indexOf(selected!)))
          const field = event.currentTarget.previousElementSibling as HTMLInputElement
          field.focus()
        }}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" strokeWidth="2.5" />
        </svg>
      </button>

      {open && (
        <ul ref={list} id={`${id}-list`} role="listbox" className="combobox-list">
          {visible.map((option, index) => (
            <li
              key={option.value}
              id={`${id}-option-${index}`}
              role="option"
              aria-selected={option.value === value}
              className={index === active ? 'active' : undefined}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => setActive(index)}
              onClick={() => choose(option)}
            >
              {option.label}
            </li>
          ))}
          {visible.length === 0 && <li className="combobox-empty">No {noun} matches.</li>}
        </ul>
      )}

      {error && (
        <p id={`${id}-error`} className="note error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
