const esbuild = require('esbuild')
const isWatch = process.argv.includes('--watch')
const isProd = process.argv.includes('--production')

const baseOpts = {
  bundle: true,
  minify: isProd,
  sourcemap: !isProd,
  external: ['vscode'],
}

async function build() {
  const ctx = await esbuild.context({
    ...baseOpts,
    entryPoints: ['src/extension.ts'],
    outfile: 'out/extension.js',
    platform: 'node',
    format: 'cjs',
  })
  if (isWatch) {
    await ctx.watch()
    console.log('Watching...')
  } else {
    await ctx.rebuild()
    await ctx.dispose()
    console.log('Build complete.')
  }
}

build().catch((e) => { console.error(e); process.exit(1) })
