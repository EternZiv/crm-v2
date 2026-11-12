const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const source = name => fs.readFileSync(path.join(root, 'static/assets/js', name), 'utf8');
const png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=';

function setup() {
    const scripts = [], downloads = [], alerts = [];
    const chart = { getDataURL: () => png, resize() {}, isDisposed: () => false };
    const context = vm.createContext({
        window: {}, console: { error() {} }, alert: message => alerts.push(message),
        echarts: { getInstanceByDom: () => chart },
        document: {
            getElementById: () => ({}),
            querySelector: selector => scripts.find(s => selector.includes(s.src)) || null,
            createElement: tag => tag === 'a'
                ? { click() { downloads.push({ filename: this.download, url: this.href }); } }
                : { dataset: {}, remove() { scripts.splice(scripts.indexOf(this), 1); } },
            head: { appendChild: script => scripts.push(script) }
        }
    });
    vm.runInContext(source('finlo_charts.js'), context);
    const loadExports = () => {
        vm.runInContext(source('finlo_chart_exports.js'), context);
        scripts[0].onload();
    };
    return { context, api: context.EChartsConfig, chart, scripts, downloads, alerts, loadExports };
}

test('PNG exports load one shared module only on click and reuse it', async () => {
    const h = setup();
    assert.equal(h.scripts.length, 0);
    const first = h.api.exportChart(h.chart, 'first', 'png');
    const second = h.api.exportChart(h.chart, 'second', 'png');
    assert.equal(h.scripts.length, 1);
    h.loadExports();
    await Promise.all([first, second]);
    assert.deepEqual(h.downloads.map(d => d.filename), ['first.png', 'second.png']);
    assert.ok(h.downloads.every(d => d.url.startsWith('data:image/png;base64,')));
    assert.equal(h.scripts.length, 1); // No PDF library for PNG.
    h.api.exportChart(h.chart, 'third', 'png');
    assert.equal(h.scripts.length, 1);
    assert.equal(h.alerts.length, 0);
});

test('failed export-module load can be retried', async () => {
    const h = setup();
    const failed = h.api.exportChart(h.chart, 'first', 'png');
    h.scripts[0].onerror();
    await failed;
    assert.equal(h.scripts.length, 0);
    const retry = h.api.exportChart(h.chart, 'retry', 'png');
    h.loadExports();
    await retry;
    assert.equal(h.downloads[0].filename, 'retry.png');
});

test('PDF requests load jsPDF on demand and generate a valid PDF', async () => {
    const h = setup();
    const request = h.api.exportChartAsPDF('chart-id', 'report');
    h.loadExports();
    await request;
    assert.equal(h.scripts.length, 2);
    assert.match(h.scripts[1].src, /jspdf/);
    const { jsPDF } = require(path.join(root, 'static/assets/js/jspdf/jspdf.umd.min.js'));
    let result;
    h.context.window.jspdf = { jsPDF: function(options) {
        const pdf = new jsPDF(options);
        pdf.save = filename => { result = { filename, bytes: Buffer.from(pdf.output('arraybuffer')) }; };
        return pdf;
    } };
    h.scripts[1].onload();
    assert.equal(h.alerts.length, 0);
    assert.equal(result.filename, 'report.pdf');
    assert.equal(result.bytes.subarray(0, 5).toString(), '%PDF-');
    assert.ok(result.bytes.length > 500);
    assert.equal(h.scripts.length, 2);
});
