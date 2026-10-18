/**
 * Automated Accessibility Auditor (2026)
 * Uses axe-core with Puppeteer/Playwright to audit web pages for WCAG 2.2 AA violations.
 * 
 * Usage:
 *   node scripts/audit-axe.js <url> [--output=json|markdown]
 */

const fs = require('fs');
const path = require('path');

async function runAudit() {
  const args = process.argv.slice(2);
  const targetUrl = args.find(a => !a.startsWith('--')) || 'http://localhost:3000';
  const formatArg = args.find(a => a.startsWith('--output=')) || '--output=markdown';
  const format = formatArg.split('=')[1];

  console.log(`[a11y-audit] Starting WCAG 2.2 AA audit for: ${targetUrl}`);
  
  // Note: Ensure puppeteer and @axe-core/puppeteer are installed or available in target env
  try {
    const puppeteer = require('puppeteer');
    const { AxePuppeteer } = require('@axe-core/puppeteer');

    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });

    console.log(`[a11y-audit] Navigating to ${targetUrl}...`);
    await page.goto(targetUrl, { waitUntil: 'networkidle2' });

    console.log(`[a11y-audit] Running axe-core scan...`);
    const results = await new AxePuppeteer(page)
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'cat.aria', 'cat.keyboard'])
      .analyze();

    await browser.close();

    const timestamp = new Date().toISOString().replace(/:/g, '-');
    const reportFileName = `audit-report-${timestamp}.${format === 'json' ? 'json' : 'md'}`;
    const reportPath = path.join(process.cwd(), reportFileName);

    if (format === 'json') {
      fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
    } else {
      let md = `# Accessibility Audit Report\n\n`;
      md += `- **Target URL**: ${results.url}\n`;
      md += `- **Timestamp**: ${results.timestamp}\n`;
      md += `- **Passes**: ${results.passes.length}\n`;
      md += `- **Violations**: ${results.violations.length}\n`;
      md += `- **Incomplete**: ${results.incomplete.length}\n\n`;

      if (results.violations.length === 0) {
        md += `## 🎉 No WCAG 2.2 AA violations detected by axe-core!\n\n`;
        md += `*Remember: Automated testing covers ~30-40% of WCAG criteria. Perform manual keyboard and screen reader testing for full conformance.*\n`;
      } else {
        md += `## ⚠️ Violations Found (${results.violations.length})\n\n`;
        results.violations.forEach((v, index) => {
          md += `### ${index + 1}. [${v.impact.toUpperCase()}] ${v.help} (${v.id})\n`;
          md += `- **WCAG Tags**: ${v.tags.join(', ')}\n`;
          md += `- **Description**: ${v.description}\n`;
          md += `- **Help URL**: [${v.helpUrl}](${v.helpUrl})\n`;
          md += `- **Affected Elements** (${v.nodes.length}):\n`;
          v.nodes.forEach(node => {
            md += `  - Target: \`${node.target.join(' ')}\`\n`;
            md += `    - Summary: ${node.failureSummary}\n`;
          });
          md += `\n`;
        });
      }

      fs.writeFileSync(reportPath, md);
    }

    console.log(`[a11y-audit] Report saved successfully to: ${reportPath}`);
  } catch (err) {
    console.error(`[a11y-audit] Error during audit:`, err.message);
    console.log(`[a11y-audit] Make sure to install dependencies: npm install puppeteer @axe-core/puppeteer`);
    process.exitCode = 1;
  }
}

if (require.main === module) {
  runAudit();
}
