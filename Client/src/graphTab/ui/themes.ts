import themesData from './themes.json'
import { vscode } from './api'
import {
  applyGraphTheme,
  getLinkColors,
  getNodeColors,
  NODE_COLOR_KEYS,
  LINK_COLOR_KEYS,
} from './graph'

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


function loadPersistedThemes() {
  const state = vscode.getState() as WebviewThemeState | null
  if (state?.userThemes?.length) {
    allThemes = [...builtInThemes, ...state.userThemes.map(t => ({ ...t, custom: true }))]
  }
  if (state?.activeThemeName) {
    const found = allThemes.find(t => t.name === state.activeThemeName)
    if (found) activeThemeName = found.name
  }
}

function persistUserThemes() {
  const state = (vscode.getState() as WebviewThemeState | null) ?? {}
  vscode.setState({
    ...state,
    userThemes: allThemes.filter(t => t.custom).map(t => ({
      name: t.name,
      nodeColors: { ...t.nodeColors },
      linkColors: { ...t.linkColors },
    })),
    activeThemeName,
  })
}

function getAllThemes(): GraphTheme[] {
  return allThemes
}

function selectTheme(theme: GraphTheme) {
  activeThemeName = theme.name
  applyGraphTheme(theme.nodeColors, theme.linkColors)
  persistUserThemes()
}

function defaultThemeName(): string {
  const themeNumbers = allThemes
    .map(t => /^Theme (\d+)$/.exec(t.name))
    .filter((m): m is RegExpExecArray => m !== null)
    .map(m => parseInt(m[1], 10))
  const next = themeNumbers.length ? Math.max(...themeNumbers) + 1 : 1
  return `Theme ${next}`
}

function saveCustomTheme(nameInput: HTMLInputElement): string | null {
  const draft = customDraft ?? {
    name: '',
    nodeColors: { ...getNodeColors() },
    linkColors: { ...getLinkColors() },
  }
  const name = nameInput.value.trim() || defaultThemeName()
  if (allThemes.some(t => t.name === name)) {
    return `A theme named "${name}" already exists`
  }

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

  const panel = document.getElementById('theme-panel')!
  const openBtn = document.getElementById('theme-btn')!
  const closeBtn = document.getElementById('close-theme-btn')!
  const tabThemes = document.getElementById('theme-tab-themes')!
  const tabCustom = document.getElementById('theme-tab-custom')!
  const themesView = document.getElementById('theme-themes-view')!
  const customView = document.getElementById('theme-custom-view')!
  const themeList = document.getElementById('theme-list')!
  const customColorList = document.getElementById('theme-custom-colors')!
  const themeNameInput = document.getElementById('theme-name-input') as HTMLInputElement
  const saveThemeBtn = document.getElementById('save-theme-btn')!
  const saveThemeStatus = document.getElementById('save-theme-status')!

  function setTab(tab: 'themes' | 'custom') {
    tabThemes.classList.toggle('active', tab === 'themes')
    tabCustom.classList.toggle('active', tab === 'custom')
    themesView.style.display = tab === 'themes' ? 'flex' : 'none'
    customView.style.display = tab === 'custom' ? 'flex' : 'none'
    if (tab === 'themes') renderThemesList()
    else renderCustomEditor()
  }

  function renderThemesList() {
    themeList.innerHTML = ''
    getAllThemes().forEach(theme => {
      const item = document.createElement('button')
      item.type = 'button'
      item.className = 'theme-list-item' + (theme.name === activeThemeName ? ' active' : '')
      const previewColors = { ...theme.nodeColors, ...theme.linkColors }
      const previewKeys = [...NODE_COLOR_KEYS.slice(0, 5), ...LINK_COLOR_KEYS.slice(0, 3)]
      item.innerHTML = `
        <span class="theme-list-name">${theme.name}${theme.custom ? ' <span class="theme-custom-badge">Custom</span>' : ''}</span>
        <span class="theme-list-preview">${renderThemePreview(previewColors, previewKeys)}</span>
      `
      item.addEventListener('click', () => {
        selectTheme(theme)
        renderThemesList()
      })
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

    const addSection = (title: string, keys: string[], target: 'nodeColors' | 'linkColors') => {
      const heading = document.createElement('div')
      heading.className = 'theme-custom-section-title'
      heading.textContent = title
      customColorList.appendChild(heading)

      keys.forEach(key => {
        const row = document.createElement('label')
        row.className = 'theme-color-row'
        const color = draft[target][key] || '#aaaaaa'
        row.innerHTML = `
          <span class="theme-color-label">${key}</span>
          <input type="color" class="theme-color-picker" value="${normalizeHex(color)}" data-target="${target}" data-key="${key}">
          <span class="theme-color-hex">${color}</span>
        `
        const picker = row.querySelector('.theme-color-picker') as HTMLInputElement
        const hexEl = row.querySelector('.theme-color-hex')!
        picker.addEventListener('input', () => {
          draft[target][key] = picker.value
          hexEl.textContent = picker.value
          applyGraphTheme(draft.nodeColors, draft.linkColors)
        })
        customColorList.appendChild(row)
      })
    }

    addSection('Nodes', NODE_COLOR_KEYS, 'nodeColors')
    addSection('Links', LINK_COLOR_KEYS, 'linkColors')
  }

  openBtn.addEventListener('click', () => {
    panel.classList.add('open')
    setTab('themes')
  })

  closeBtn.addEventListener('click', () => panel.classList.remove('open'))

  panel.addEventListener('click', (e) => {
    if (e.target === panel) panel.classList.remove('open')
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
