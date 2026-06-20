import './themes.css'
import './colorpicker.css'
import themesData from './themes.json'
import { vscode } from '../api'
import {
  applyGraphTheme,
  getLinkColors,
  getNodeColors,
  NODE_COLOR_KEYS,
  LINK_COLOR_KEYS,
} from '../graph/graph'

export interface GraphTheme {
  name: string
  nodeColors: Record<string, string>
  linkColors: Record<string, string>
  custom?: boolean
}

type WebviewThemeState = {
  userThemes?: GraphTheme[]
  activeThemeName?: string
}

const builtInThemes: GraphTheme[] = themesData.themes.map(t => ({
  ...t,
  custom: false,
}))

let allThemes: GraphTheme[] = [...builtInThemes]
let activeThemeName = builtInThemes[0]?.name ?? 'Default'
let customDraft: GraphTheme | null = null

// ─── Custom Color Picker ──────────────────────────────────────────────────────

type PickerCb = (hex: string) => void

let _pEl: HTMLElement | null = null
let _pH = 0, _pS = 1, _pV = 1
let _pCb: PickerCb | null = null

function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  const i = Math.floor(h / 60) % 6
  const f = h / 60 - Math.floor(h / 60)
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s)
  const lut: [number, number, number][] = [
    [v,t,p],[q,v,p],[p,v,t],[p,q,v],[t,p,v],[v,p,q],
  ]
  return lut[i].map(x => Math.round(x * 255)) as [number, number, number]
}

function rgbToHsv(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min
  let h = 0
  const s = max ? d / max : 0
  if (d) {
    if      (max === r) h = 60 * (((g - b) / d) % 6)
    else if (max === g) h = 60 * ((b - r) / d + 2)
    else                h = 60 * ((r - g) / d + 4)
    if (h < 0) h += 360
  }
  return [h, s, max]
}

function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(hex.trim())
  if (!m) return null
  const n = parseInt(m[1], 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase()
}

function syncPicker(skipCb = false) {
  const el = _pEl
  if (!el) return

  const hueSlider = el.querySelector('.vcp-hue')      as HTMLInputElement
  const satSlider = el.querySelector('.vcp-sat')      as HTMLInputElement
  const valSlider = el.querySelector('.vcp-val')      as HTMLInputElement
  const satTrack  = el.querySelector('.vcp-sat-track') as HTMLElement
  const valTrack  = el.querySelector('.vcp-val-track') as HTMLElement
  const rIn       = el.querySelector('.vcp-r')        as HTMLInputElement
  const gIn       = el.querySelector('.vcp-g')        as HTMLInputElement
  const bIn       = el.querySelector('.vcp-b')        as HTMLInputElement
  const hexIn     = el.querySelector('.vcp-hex')      as HTMLInputElement
  const preview   = el.querySelector('.vcp-preview')  as HTMLElement

  hueSlider.value = String(Math.round(_pH))
  satSlider.value = String(Math.round(_pS * 100))
  valSlider.value = String(Math.round(_pV * 100))

  const hueHsl  = `hsl(${Math.round(_pH)},100%,50%)`
  const grayAtV = `hsl(0,0%,${Math.round(_pV * 100)}%)`
  satTrack.style.background = `linear-gradient(to right, ${grayAtV}, ${hueHsl})`
  valTrack.style.background = `linear-gradient(to right, #000, ${hueHsl})`

  const [r, g, b] = hsvToRgb(_pH, _pS, _pV)
  const hex = rgbToHex(r, g, b)
  rIn.value   = String(r)
  gIn.value   = String(g)
  bIn.value   = String(b)
  hexIn.value = hex
  preview.style.background = hex

  if (!skipCb && _pCb) _pCb(hex)
}

function buildPicker(): HTMLElement {
  const el = document.createElement('div')
  el.className = 'vcp-popup'
  el.innerHTML = `
    <div class="vcp-top-row">
      <div class="vcp-preview"></div>
      <div class="vcp-top-hex">
        <input type="text" class="vcp-hex vcp-text" maxlength="7" spellcheck="false" placeholder="#000000">
        <span class="vcp-hex-label">Hex</span>
      </div>
    </div>
    <div class="vcp-sliders">
      <div class="vcp-slider-row">
        <span class="vcp-slider-label">H</span>
        <div class="vcp-track vcp-hue-track">
          <input type="range" class="vcp-hue vcp-slider" min="0" max="360" step="1">
        </div>
      </div>
      <div class="vcp-slider-row">
        <span class="vcp-slider-label">S</span>
        <div class="vcp-track vcp-sat-track">
          <input type="range" class="vcp-sat vcp-slider" min="0" max="100" step="1">
        </div>
      </div>
      <div class="vcp-slider-row">
        <span class="vcp-slider-label">V</span>
        <div class="vcp-track vcp-val-track">
          <input type="range" class="vcp-val vcp-slider" min="0" max="100" step="1">
        </div>
      </div>
    </div>
    <div class="vcp-rgb-row">
      <div class="vcp-col">
        <input type="number" class="vcp-r vcp-num" min="0" max="255">
        <span>R</span>
      </div>
      <div class="vcp-col">
        <input type="number" class="vcp-g vcp-num" min="0" max="255">
        <span>G</span>
      </div>
      <div class="vcp-col">
        <input type="number" class="vcp-b vcp-num" min="0" max="255">
        <span>B</span>
      </div>
    </div>
  `
  document.body.appendChild(el)

  const hueSlider = el.querySelector('.vcp-hue') as HTMLInputElement
  hueSlider.addEventListener('input', () => { _pH = parseFloat(hueSlider.value); syncPicker() })

  const satSlider = el.querySelector('.vcp-sat') as HTMLInputElement
  satSlider.addEventListener('input', () => { _pS = parseInt(satSlider.value) / 100; syncPicker() })

  const valSlider = el.querySelector('.vcp-val') as HTMLInputElement
  valSlider.addEventListener('input', () => { _pV = parseInt(valSlider.value) / 100; syncPicker() })

  const rIn = el.querySelector('.vcp-r') as HTMLInputElement
  const gIn = el.querySelector('.vcp-g') as HTMLInputElement
  const bIn = el.querySelector('.vcp-b') as HTMLInputElement
  function onRgb() {
    const rgb: [number, number, number] = [
      Math.max(0, Math.min(255, parseInt(rIn.value) || 0)),
      Math.max(0, Math.min(255, parseInt(gIn.value) || 0)),
      Math.max(0, Math.min(255, parseInt(bIn.value) || 0)),
    ]
    ;[_pH, _pS, _pV] = rgbToHsv(...rgb)
    syncPicker()
  }
  rIn.addEventListener('input', onRgb)
  gIn.addEventListener('input', onRgb)
  bIn.addEventListener('input', onRgb)

  const hexIn = el.querySelector('.vcp-hex') as HTMLInputElement
  hexIn.addEventListener('input', () => {
    const rgb = hexToRgb(hexIn.value)
    if (rgb) { ;[_pH, _pS, _pV] = rgbToHsv(...rgb); syncPicker() }
  })

  document.addEventListener('mousedown', e => {
    if (!_pEl || _pEl.style.display === 'none') return
    const t = e.target as Element
    if (_pEl.contains(t) || t.closest('.theme-color-swatch-wrap')) return
    closeColorPicker()
  }, true)

  return el
}

function openColorPicker(anchor: HTMLElement, hex: string, cb: PickerCb) {
  if (!_pEl) _pEl = buildPicker()

  const rgb = hexToRgb(hex) ?? ([170, 170, 170] as [number, number, number])
  ;[_pH, _pS, _pV] = rgbToHsv(...(rgb as [number, number, number]))
  _pCb = null

  _pEl.style.display = 'block'

  requestAnimationFrame(() => {
    const el = _pEl!
    const aRect = anchor.getBoundingClientRect()
    const pw = el.offsetWidth  || 256
    const ph = el.offsetHeight || 220
    let left = aRect.left
    let top  = aRect.bottom + 8
    if (left + pw > window.innerWidth  - 8) left = window.innerWidth  - pw - 8
    if (top  + ph > window.innerHeight - 8) top  = aRect.top - ph - 8
    el.style.left = Math.max(4, left) + 'px'
    el.style.top  = Math.max(4, top)  + 'px'
    _pCb = cb
    syncPicker(false)
  })
}

function closeColorPicker() {
  if (_pEl) { _pEl.style.display = 'none'; _pCb = null }
}

// ─── Theme persistence ────────────────────────────────────────────────────────

function loadPersistedThemes() {
  const extState = (window as any).THEME_STATE as WebviewThemeState | null
  const state = extState || (vscode.getState() as WebviewThemeState | null)
  if (state?.userThemes?.length) {
    allThemes = [...builtInThemes, ...state.userThemes.map(t => ({ ...t, custom: true }))]
  }
  if (state?.activeThemeName) {
    const found = allThemes.find(t => t.name === state.activeThemeName)
    if (found) activeThemeName = found.name
  }
}

function persistUserThemes() {
  const state = {
    ...((vscode.getState() as WebviewThemeState | null) ?? {}),
    userThemes: allThemes.filter(t => t.custom).map(t => ({
      name: t.name,
      nodeColors: { ...t.nodeColors },
      linkColors: { ...t.linkColors },
    })),
    activeThemeName,
  }
  vscode.setState(state)
  vscode.postMessage({ command: 'saveThemeState', state })
}

function getAllThemes(): GraphTheme[] { return allThemes }

function selectTheme(theme: GraphTheme) {
  activeThemeName = theme.name
  applyGraphTheme(theme.nodeColors, theme.linkColors)
  persistUserThemes()
}

function defaultThemeName(): string {
  const nums = allThemes
    .map(t => /^Theme (\d+)$/.exec(t.name))
    .filter((m): m is RegExpExecArray => m !== null)
    .map(m => parseInt(m[1], 10))
  return `Theme ${nums.length ? Math.max(...nums) + 1 : 1}`
}

function saveCustomTheme(nameInput: HTMLInputElement): string | null {
  const draft = customDraft ?? {
    name: '',
    nodeColors: { ...getNodeColors() },
    linkColors: { ...getLinkColors() },
  }
  const name = nameInput.value.trim() || defaultThemeName()
  if (allThemes.some(t => t.name === name)) return `A theme named "${name}" already exists`

  const theme: GraphTheme = {
    name,
    nodeColors: { ...draft.nodeColors },
    linkColors: { ...draft.linkColors },
    custom: true,
  }
  allThemes.push(theme)
  activeThemeName = name
  applyGraphTheme(theme.nodeColors, theme.linkColors)
  persistUserThemes()
  nameInput.value = ''
  customDraft = null
  return null
}

function renderThemePreview(colors: Record<string, string>, keys: string[]): string {
  return keys
    .map(key => `<span class="theme-preview-swatch" style="background:${colors[key] || '#aaa'}" title="${key}"></span>`)
    .join('')
}

export function initTheme() {
  loadPersistedThemes()

  const initial = allThemes.find(t => t.name === activeThemeName) ?? builtInThemes[0]
  if (initial) applyGraphTheme(initial.nodeColors, initial.linkColors)

  const panel           = document.getElementById('theme-panel')!
  const openBtn         = document.getElementById('theme-btn')!
  const closeBtn        = document.getElementById('close-theme-btn')!
  const tabThemes       = document.getElementById('theme-tab-themes')!
  const tabCustom       = document.getElementById('theme-tab-custom')!
  const themesView      = document.getElementById('theme-themes-view')!
  const customView      = document.getElementById('theme-custom-view')!
  const themeList       = document.getElementById('theme-list')!
  const customColorList = document.getElementById('theme-custom-colors')!
  const themeNameInput  = document.getElementById('theme-name-input') as HTMLInputElement
  const saveThemeBtn    = document.getElementById('save-theme-btn')!
  const saveThemeStatus = document.getElementById('save-theme-status')!

  function setTab(tab: 'themes' | 'custom') {
    tabThemes.classList.toggle('active', tab === 'themes')
    tabCustom.classList.toggle('active', tab === 'custom')
    themesView.style.display = tab === 'themes' ? 'flex' : 'none'
    customView.style.display = tab === 'custom' ? 'flex' : 'none'
    if (tab === 'themes') renderThemesList()
    else renderCustomEditor()
  }

  function deleteTheme(name: string) {
    allThemes = allThemes.filter(t => t.name !== name)
    if (activeThemeName === name) {
      const fallback = builtInThemes[0]
      if (fallback) selectTheme(fallback)
    } else {
      persistUserThemes()
    }
    renderThemesList()
  }

  function renderThemesList() {
    themeList.innerHTML = ''
    let addedCustomDivider = false

    getAllThemes().forEach(theme => {
      if (theme.custom && !addedCustomDivider) {
        addedCustomDivider = true
        const divider = document.createElement('div')
        divider.className = 'theme-list-divider'
        divider.textContent = 'Custom Themes'
        themeList.appendChild(divider)
      }

      const item = document.createElement('div')
      item.className = 'theme-list-item' + (theme.name === activeThemeName ? ' active' : '')
      const previewColors = { ...theme.nodeColors, ...theme.linkColors }
      const previewKeys = [...NODE_COLOR_KEYS.slice(0, 5)]
      
      let html = `
        <div class="theme-list-item-content">
          <div class="theme-list-name-container">
            <span class="theme-list-name" title="${theme.name}">${theme.name}</span>
          </div>
          <span class="theme-list-preview">
            ${renderThemePreview(previewColors, previewKeys)}
          </span>
        </div>
      `
      if (theme.custom) {
        html += `<button type="button" class="theme-delete-btn" title="Delete theme">✕</button>`
      } else {
        html += `<div class="theme-delete-placeholder"></div>`
      }
      item.innerHTML = html

      const content = item.querySelector('.theme-list-item-content') as HTMLElement
      content.addEventListener('click', () => { selectTheme(theme); renderThemesList() })

      const delBtn = item.querySelector('.theme-delete-btn') as HTMLButtonElement | null
      if (delBtn) {
        delBtn.addEventListener('click', (e) => {
          e.stopPropagation()
          deleteTheme(theme.name)
        })
      }

      themeList.appendChild(item)
    })
  }

  function ensureCustomDraft() {
    if (!customDraft) {
      customDraft = {
        name: '',
        nodeColors: { ...getNodeColors() },
        linkColors: { ...getLinkColors() },
        custom: true,
      }
    }
    return customDraft
  }

  function renderCustomEditor() {
    const draft = ensureCustomDraft()
    customColorList.innerHTML = ''

    const addSection = (title: string, keys: readonly string[], target: 'nodeColors' | 'linkColors') => {
      const heading = document.createElement('div')
      heading.className = 'theme-custom-section-title'
      heading.textContent = title
      customColorList.appendChild(heading)

      keys.forEach(key => {
        const row = document.createElement('div')
        row.className = 'theme-color-row'
        const normColor = normalizeHex(draft[target][key] || '#aaaaaa')
        row.innerHTML = `
          <span class="theme-color-label">${key}</span>
          <div class="theme-color-swatch-wrap">
            <div class="theme-color-swatch" style="background:${normColor}" title="Click to pick"></div>
          </div>
          <input type="text" class="theme-color-hex-input" value="${normColor}" maxlength="7" spellcheck="false">
        `
        const swatch   = row.querySelector('.theme-color-swatch') as HTMLElement
        const hexInput = row.querySelector('.theme-color-hex-input') as HTMLInputElement

        swatch.addEventListener('click', e => {
          e.stopPropagation()
          openColorPicker(swatch, draft[target][key] || '#aaaaaa', hex => {
            draft[target][key] = hex
            swatch.style.background = hex
            hexInput.value = hex
            applyGraphTheme(draft.nodeColors, draft.linkColors)
          })
        })

        hexInput.addEventListener('input', () => {
          const val = hexInput.value.trim()
          if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            draft[target][key] = val
            swatch.style.background = val
            applyGraphTheme(draft.nodeColors, draft.linkColors)
          }
        })

        hexInput.addEventListener('blur', () => {
          if (!/^#[0-9a-fA-F]{6}$/.test(hexInput.value.trim())) {
            hexInput.value = draft[target][key] || '#aaaaaa'
          }
        })

        customColorList.appendChild(row)
      })
    }

    addSection('Nodes', NODE_COLOR_KEYS, 'nodeColors')
    addSection('Links', LINK_COLOR_KEYS, 'linkColors')
  }

  openBtn.addEventListener('click', () => { panel.classList.add('open'); setTab('themes') })

  closeBtn.addEventListener('click', () => {
    panel.classList.remove('open')
    closeColorPicker()
  })

  panel.addEventListener('click', e => {
    if (e.target === panel) { panel.classList.remove('open'); closeColorPicker() }
  })

  tabThemes.addEventListener('click', () => setTab('themes'))
  tabCustom.addEventListener('click', () => {
    customDraft = {
      name: '',
      nodeColors: { ...getNodeColors() },
      linkColors: { ...getLinkColors() },
      custom: true,
    }
    setTab('custom')
  })

  saveThemeBtn.addEventListener('click', () => {
    if (!customDraft) {
      customDraft = {
        name: '',
        nodeColors: { ...getNodeColors() },
        linkColors: { ...getLinkColors() },
        custom: true,
      }
    }
    const err = saveCustomTheme(themeNameInput)
    if (err) {
      saveThemeStatus.textContent = err
      saveThemeStatus.className = 'theme-save-status error'
    } else {
      saveThemeStatus.textContent = 'Theme saved!'
      saveThemeStatus.className = 'theme-save-status success'
      setTab('themes')
    }
  })

  themeNameInput.placeholder = defaultThemeName()
  themeNameInput.addEventListener('focus', () => {
    if (!themeNameInput.value) themeNameInput.placeholder = defaultThemeName()
  })
}

function normalizeHex(color: string): string {
  if (/^#[0-9a-fA-F]{6}$/.test(color)) return color
  if (/^#[0-9a-fA-F]{8}$/.test(color)) return color.slice(0, 7)
  return '#aaaaaa'
}
