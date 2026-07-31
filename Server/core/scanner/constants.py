DEFAULT_IGNORE_PATTERNS: list[str] = [
    "node_modules", "dist",
    "build", ".git",
    "__pycache__", ".venv", "venv",
    ".next", "out", "coverage",
    "vendor", ".yarn", "pnpm-lock",
    "generated", "__mocks__", ".turbo", "DS_Store",
    "storybook-static", ".vivian-cache.json", ".vivian",
    # .NET / C# / VB.NET build output — can contain tens of thousands of files
    "bin", "obj", ".vs", ".idea", "packages",
]

SUPPORTED_EXTENSIONS: set[str] = {
    ".ts", ".tsx",
    ".js", ".jsx",
    ".py", ".go",
    ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp",
    ".cs",
    ".dart",           # Flutter / Dart
    ".swift",          # iOS / macOS
    ".kt", ".kts",     # Android / Kotlin
}

DEFAULT_MAX_DEPTH: int = 15

CACHE_FILE_NAME: str = ".vivian-cache.json"
GRAPH_FILE_NAME: str = "graph.json"
