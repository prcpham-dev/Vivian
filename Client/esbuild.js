const esbuild = require('esbuild')
const isWatch = process.argv.includes('--watch')
const isProd = process.argv.includes('--production')

const fs = require('fs')
const path = require('path')

const baseOpts = {
  bundle: true,
  minify: isProd,
  sourcemap: !isProd,
}

function copyMcpSetupAssets() {
  const srcHtml = path.join(__dirname, 'src', 'mcpSetupTab', 'ui', 'index.html')
  const srcCss = path.join(__dirname, 'src', 'mcpSetupTab', 'ui', 'style.css')
  const destHtml = path.join(__dirname, 'out', 'mcpSetup.html')
  const destCss = path.join(__dirname, 'out', 'mcpSetup.css')
  fs.mkdirSync(path.dirname(destHtml), { recursive: true })
  fs.copyFileSync(srcHtml, destHtml)
  fs.copyFileSync(srcCss, destCss)
}

async function build() {
  copyMcpSetupAssets()
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

  const mcpSetupCtx = await esbuild.context({
    ...baseOpts,
    entryPoints: ['src/mcpSetupTab/ui/index.ts'],
    outfile: 'out/mcpSetup.js',
    platform: 'browser',
    format: 'iife',
  })

  if (isWatch) {
    await ctx.watch()
    await webviewCtx.watch()
    await graphAppCtx.watch()
    await mcpSetupCtx.watch()
    console.log('Watching...')
  } else {
    await ctx.rebuild()
    await webviewCtx.rebuild()
    await graphAppCtx.rebuild()
    await mcpSetupCtx.rebuild()
    await ctx.dispose()
    await webviewCtx.dispose()
    await graphAppCtx.dispose()
    await mcpSetupCtx.dispose()
    console.log('Build complete.')
  }
}

build().catch((e) => { console.error(e); process.exit(1) })
