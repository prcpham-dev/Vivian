const esbuild = require('esbuild')
const isWatch = process.argv.includes('--watch')
const isProd = process.argv.includes('--production')

const baseOpts = {
  bundle: true,
  minify: isProd,
  sourcemap: !isProd,
}

async function build() {
  const ctx = await esbuild.context({
    ...baseOpts,
    entryPoints: ['src/extension.ts'],
    outfile: 'out/extension.js',
    platform: 'node',
    format: 'cjs',
    external: ['vscode'],
  })

  const webviewCtx = await esbuild.context({
    ...baseOpts,
    entryPoints: ['src/vulnTab/ui/index.tsx'],
    outfile: 'out/vulnManager.js',
    platform: 'browser',
    format: 'iife',
  })

  const graphAppCtx = await esbuild.context({
    ...baseOpts,
    entryPoints: ['src/graphTab/ui/index.ts'],
    outfile: 'out/graphApp.js',
    platform: 'browser',
    format: 'iife',
  })

  if (isWatch) {
    await ctx.watch()
    await webviewCtx.watch()
    await graphAppCtx.watch()
    console.log('Watching...')
  } else {
    await ctx.rebuild()
    await webviewCtx.rebuild()
    await graphAppCtx.rebuild()
    await ctx.dispose()
    await webviewCtx.dispose()
    await graphAppCtx.dispose()
    console.log('Build complete.')
  }
}

build().catch((e) => { console.error(e); process.exit(1) })
