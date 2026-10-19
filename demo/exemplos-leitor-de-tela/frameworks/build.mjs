// Compila os exemplos de React, Vue, Svelte e Angular para pacotes estáticos app-*.js na pasta de cima.
// Uso: npm install && node build.mjs   (os pacotes gerados ficam versionados, para os testes não dependerem de npm)
import { build } from 'esbuild';
import { compile } from 'svelte/compiler';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const aqui = dirname(fileURLToPath(import.meta.url));
const saida = join(aqui, '..');
const comum = { bundle: true, minify: true, format: 'iife', platform: 'browser', target: 'es2022', legalComments: 'none', logLevel: 'warning' };
const avisosSvelte = [];

const pluginSvelte = {
  name: 'svelte',
  setup(b) {
    b.onLoad({ filter: /\.svelte$/ }, (args) => {
      const fonte = readFileSync(args.path, 'utf8');
      const nome = args.path.split(/[\/]/).pop();
      const r = compile(fonte, { filename: nome, generate: 'client', dev: false });
      for (const w of r.warnings) avisosSvelte.push({ arquivo: nome, codigo: w.code, mensagem: w.message });
      return { contents: r.js.code, loader: 'js' };
    });
  },
};

await build({ ...comum, entryPoints: [join(aqui, 'src/react.jsx')], outfile: join(saida, 'app-react.js'), jsx: 'automatic', define: { 'process.env.NODE_ENV': '"production"' } });
await build({
  ...comum, entryPoints: [join(aqui, 'src/vue.js')], outfile: join(saida, 'app-vue.js'),
  alias: { vue: 'vue/dist/vue.esm-bundler.js' },
  define: { __VUE_OPTIONS_API__: 'true', __VUE_PROD_DEVTOOLS__: 'false', __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false', 'process.env.NODE_ENV': '"production"' },
});
await build({ ...comum, entryPoints: [join(aqui, 'src/svelte.js')], outfile: join(saida, 'app-svelte.js'), plugins: [pluginSvelte], conditions: ['browser', 'svelte'] });
writeFileSync(join(saida, 'app-svelte.avisos.json'), JSON.stringify(avisosSvelte, null, 2) + '\n');
await build({
  ...comum, entryPoints: [join(aqui, 'src/angular.ts')], outfile: join(saida, 'app-angular.js'),
  tsconfigRaw: { compilerOptions: { experimentalDecorators: true, useDefineForClassFields: false, target: 'es2022' } },
  define: { ngDevMode: 'false', ngJitMode: 'true' },
});
console.log('pacotes gerados em', saida);
