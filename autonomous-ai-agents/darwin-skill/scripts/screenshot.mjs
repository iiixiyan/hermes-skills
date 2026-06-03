#!/usr/bin/env node
const pw = require('playwright-core');
const htmlPath = process.argv[2];
const outputPath = process.argv[3];

async function screenshot() {
  const browser = await pw.chromium.launch();
  try {
    const context = await browser.newContext({viewport:{width:920,height:1600},deviceScaleFactor:2});
    const page = await context.newPage();
    await page.goto(`file://${htmlPath}`,{waitUntil:'networkidle'});
    await page.evaluate(()=>document.fonts.ready);
    await page.waitForTimeout(2000);
    await page.locator('.card').screenshot({path:outputPath,type:'png'});
    console.log(`截图完成: ${outputPath}`);
  } finally { await browser.close(); }
}
screenshot().catch(e=>{console.error('截图失败:',e.message);process.exit(1);});