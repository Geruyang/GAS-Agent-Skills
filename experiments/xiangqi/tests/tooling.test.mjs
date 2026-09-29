import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp, mkdir, copyFile, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));

test('directory URLs redirect before the browser resolves relative scripts', async t => {
  // Change only the listening port in this isolated child; never touch a user's server.
  const bootstrap = `
    import http from 'node:http';
    const listen = http.Server.prototype.listen;
    http.Server.prototype.listen = function (...args) {
      args[0] = 0;
      this.once('listening', () => process.send({port: this.address().port}));
      return listen.apply(this, args);
    };
    await import(${JSON.stringify(pathToFileURL(path.join(root, 'serve.mjs')).href)});
  `;
  const child = spawn(process.execPath, ['--input-type=module', '--eval', bootstrap], {
    stdio: ['ignore', 'ignore', 'pipe', 'ipc']
  });
  t.after(async () => {
    if (child.exitCode === null) {
      const exited = once(child, 'exit');
      child.kill();
      await exited;
    }
  });
  const [message] = await once(child, 'message', {signal: AbortSignal.timeout(10000)});
  const origin = `http://127.0.0.1:${message.port}`;
  for (const mode of ['centralized', 'decentralized', 'combined']) {
    const response = await fetch(`${origin}/${mode}?check=1`, {redirect: 'manual'});
    assert.equal(response.status, 301, mode);
    assert.equal(response.headers.get('location'), `/${mode}/?check=1`);
    await response.text();
    const page = await fetch(new URL(response.headers.get('location'), origin));
    assert.equal(page.status, 200);
    const html = await page.text();
    const script = html.match(/<script[^>]+src="([^"]+)"/);
    assert.ok(script, `${mode} entry script`);
    const asset = await fetch(new URL(script[1], page.url));
    assert.equal(asset.status, 200);
    assert.match(asset.headers.get('content-type'), /javascript/);
    await asset.text();
  }
  const missing = await fetch(`${origin}/missing-file.js`);
  assert.equal(missing.status, 404);
  await missing.text();
  const outside = await fetch(`${origin}/%2e%2e%2fpackage.json`);
  assert.equal(outside.status, 403);
  await outside.text();
});

for (const scenario of ['pass', 'failed-test', 'missing-mode']) {
  test(`measurement exit status reflects ${scenario} and preserves the report`, async t => {
    const temporaryRoot = path.resolve(tmpdir());
    const temporary = await mkdtemp(path.join(temporaryRoot, 'gas-measure-test-'));
    t.after(() => {
      assert.equal(path.dirname(temporary), temporaryRoot);
      assert.ok(path.basename(temporary).startsWith('gas-measure-test-'));
      return rm(temporary, {recursive: true, force: true});
    });
    const fixture = path.join(temporary, 'experiments', 'xiangqi');
    await mkdir(path.join(fixture, 'tests'), {recursive: true});
    await copyFile(path.join(root, 'measure.mjs'), path.join(fixture, 'measure.mjs'));
    await writeFile(path.join(fixture, 'CONTRACT.md'), 'Isolated test contract\n');
    for (const mode of ['centralized', 'decentralized', 'combined']) {
      if (scenario === 'missing-mode' && mode === 'combined') continue;
      await mkdir(path.join(fixture, mode));
      await writeFile(path.join(fixture, mode, 'engine.js'), '// fixture\n');
    }
    await writeFile(path.join(fixture, 'tests', 'acceptance.test.mjs'),
      `import test from 'node:test';\n` +
      `test('fixture result', () => {${scenario === 'failed-test' ? "throw new Error('intentional fixture failure');" : ''}});\n`);
    const environment = {...process.env};
    delete environment.NODE_TEST_CONTEXT; // This fixture runs its own independent test runner.
    const result = spawnSync(process.execPath, [path.join(fixture, 'measure.mjs')], {env: environment, encoding: 'utf8', timeout: 30000});
    assert.equal(result.error, undefined);
    assert.equal(result.status, scenario === 'pass' ? 0 : 1);
    const report = JSON.parse(await readFile(path.join(temporary, '.gas/experiments/xiangqi-v2/external/measurement.json'), 'utf8'));
    if (scenario === 'failed-test') {
      assert.equal(report.modes.centralized.fail_count, 1);
      assert.equal(report.modes.centralized.exit_code, 1);
    } else if (scenario === 'missing-mode') {
      assert.ok(report.modes.combined.error);
    } else {
      assert.equal(report.modes.combined.pass_count, 1, result.stdout + result.stderr);
    }
  });
}
