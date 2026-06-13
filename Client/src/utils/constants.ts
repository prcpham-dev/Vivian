export const DEFAULT_PORT = 8765
export const SIDECAR_HEALTH_URL = `http://localhost:${DEFAULT_PORT}/health`
export const GRAPH_BUILD_URL = `http://localhost:${DEFAULT_PORT}/graph/build`
export const GRAPH_CACHE_URL = `http://localhost:${DEFAULT_PORT}/graph/cache/load`
export const WS_URL = `ws://localhost:${DEFAULT_PORT}/ws`
export const CACHE_FILE_NAME = '.vivian-cache.json'
export const GRAPH_FILE_NAME = 'graph.json'

export const DEFAULT_IGNORE_PATTERNS = [
  'node_modules', '.git', '__pycache__', '.venv', 'venv',
  'dist', 'build', 'out', '.next', '.nuxt', 'coverage',
  'vendor', '.yarn', 'pnpm-lock', 'generated', '__mocks__',
  '.turbo', 'storybook-static',
]

export const SUPPORTED_EXTENSIONS = ['.ts', '.js', '.tsx', '.jsx', '.py', '.go', '.rs', '.c', '.cpp']
