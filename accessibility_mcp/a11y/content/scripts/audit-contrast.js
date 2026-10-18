/**
 * Manual Color Contrast Checker (2026)
 * Computes the WCAG 2.x relative-luminance contrast ratio between two colors —
 * useful for design review (mockups, brand palettes, hover/disabled/error
 * states) before code even exists, which live-page scanners can't check.
 *
 * NOTE: automated scans via scripts/audit-axe.js already flag most in-DOM
 * contrast failures (axe-core's `color-contrast` rule is tagged wcag2aa).
 * Use THIS script for colors that aren't in a live page yet, or to sanity-check
 * a specific pair by hand.
 *
 * Usage:
 *   node scripts/audit-contrast.js <foreground> <background> [--size=<px>] [--bold]
 *
 * Examples:
 *   node scripts/audit-contrast.js "#767676" "#ffffff"
 *   node scripts/audit-contrast.js "#333" "#f5f5f5" --size=24
 *   node scripts/audit-contrast.js "rgb(0,102,204)" "#fff" --size=18.66 --bold
 *
 * Accepts #rgb, #rrggbb, and rgb()/rgba() input. Large text (per WCAG 1.4.3)
 * is >=24px normal weight, or >=18.66px (14pt) bold — pass --size and --bold
 * to auto-classify; otherwise the script reports both thresholds.
 */

function parseColor(input) {
  const s = input.trim();
  const rgbMatch = s.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i);
  if (rgbMatch) {
    return [Number(rgbMatch[1]), Number(rgbMatch[2]), Number(rgbMatch[3])];
  }
  let hex = s.replace(/^#/, '');
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
  if (!/^[0-9a-f]{6}$/i.test(hex)) {
    throw new Error(`Unrecognized color: "${input}". Use #rgb, #rrggbb, or rgb(r,g,b).`);
  }
  return [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ];
}

// WCAG 2.x relative luminance (https://www.w3.org/TR/WCAG22/#dfn-relative-luminance)
function relativeLuminance([r, g, b]) {
  const toLinear = (c) => {
    const cs = c / 255;
    return cs <= 0.04045 ? cs / 12.92 : Math.pow((cs + 0.055) / 1.055, 2.4);
  };
  const [rl, gl, bl] = [toLinear(r), toLinear(g), toLinear(b)];
  return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl;
}

function contrastRatio(rgbA, rgbB) {
  const lA = relativeLuminance(rgbA);
  const lB = relativeLuminance(rgbB);
  const [lighter, darker] = lA > lB ? [lA, lB] : [lB, lA];
  return (lighter + 0.05) / (darker + 0.05);
}

function verdict(ratio, threshold) {
  return ratio >= threshold ? 'PASS' : 'FAIL';
}

function runCheck() {
  const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
  const flags = process.argv.slice(2).filter((a) => a.startsWith('--'));
  const [fg, bg] = args;

  if (!fg || !bg) {
    console.log('Usage: node scripts/audit-contrast.js <foreground> <background> [--size=<px>] [--bold]');
    process.exit(1);
  }

  const sizeFlag = flags.find((f) => f.startsWith('--size='));
  const size = sizeFlag ? Number(sizeFlag.split('=')[1]) : null;
  const bold = flags.includes('--bold');

  const rgbFg = parseColor(fg);
  const rgbBg = parseColor(bg);
  const ratio = contrastRatio(rgbFg, rgbBg);

  console.log(`\n[contrast-audit] ${fg} on ${bg}`);
  console.log(`Contrast ratio: ${ratio.toFixed(2)}:1\n`);

  if (size !== null) {
    const isLarge = size >= 24 || (bold && size >= 18.66);
    const aaThreshold = isLarge ? 3 : 4.5;
    const aaaThreshold = isLarge ? 4.5 : 7;
    console.log(`Classified as ${isLarge ? 'LARGE' : 'NORMAL'} text (${size}px${bold ? ', bold' : ''}) — WCAG 1.4.3:`);
    console.log(`  AA  (${aaThreshold}:1):  ${verdict(ratio, aaThreshold)}`);
    console.log(`  AAA (${aaaThreshold}:1): ${verdict(ratio, aaaThreshold)}`);
  } else {
    console.log('No --size given — reporting against all WCAG 1.4.3 thresholds:');
    console.log(`  Normal text AA  (4.5:1): ${verdict(ratio, 4.5)}`);
    console.log(`  Normal text AAA (7:1):   ${verdict(ratio, 7)}`);
    console.log(`  Large text  AA  (3:1):   ${verdict(ratio, 3)}`);
    console.log(`  Large text  AAA (4.5:1): ${verdict(ratio, 4.5)}`);
  }

  console.log(`\nNote: this is the normative WCAG 2.x ratio formula. WCAG 3.0 is an`);
  console.log(`incomplete Working Draft and does not provide a stable replacement contrast`);
  console.log(`algorithm. Do not replace WCAG 2 contrast checks with draft methods.`);
  console.log(`For a second opinion, cross-check with the WebAIM Contrast Checker\n(https://webaim.org/resources/contrastchecker/).\n`);
}

if (require.main === module) {
  runCheck();
}

module.exports = { relativeLuminance, contrastRatio, parseColor };
