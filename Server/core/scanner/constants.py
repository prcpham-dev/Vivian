DEFAULT_IGNORE_PATTERNS: list[str] = [
    "node_modules", "dist",
    "build", ".git",
    "__pycache__", ".venv", "venv",
    ".next", "out", "coverage",
    "vendor", ".yarn", "pnpm-lock",
    "generated", "__mocks__", ".turbo", "DS_Store"
    "storybook-static", ".vivian-cache.json", ".vivian"
]

SUPPORTED_EXTENSIONS: set[str] = {
    ".ts", ".tsx",
    ".js", ".jsx",
    ".py", ".go",
    ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp",
}

DEFAULT_MAX_DEPTH: int = 15
MAX_FILES: int = 2_000

CACHE_FILE_NAME: str = ".vivian-cache.json"
