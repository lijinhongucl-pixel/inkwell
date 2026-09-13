#!/usr/bin/env node
/**
 * Playwright HTML → PNG 截图脚本
 *
 * 用法：
 *   node screenshot.js <input.html> <output.png> <width> <height>
 *
 * 在无头 Chromium 中打开 HTML，等待渲染稳定后截图。
 * 支持 deviceScaleFactor=2（Retina 高清输出）。
 */
const { chromium } = require('playwright-core');
const path = require('path');

async function main() {
  const [,, inputPath, outputPath, widthStr, heightStr] = process.argv;
  if (!inputPath || !outputPath || !widthStr || !heightStr) {
    console.error('用法: node screenshot.js <input.html> <output.png> <width> <height>');
    process.exit(1);
  }
  const width = parseInt(widthStr, 10);
  const height = parseInt(heightStr, 10);
  const absInput = path.resolve(inputPath);
  const absOutput = path.resolve(outputPath);

  // 可选：通过 PLAYWRIGHT_CHROMIUM_PATH 指定自定义 Chromium 可执行文件
  const launchOpts = { headless: true };
  if (process.env.PLAYWRIGHT_CHROMIUM_PATH) {
    launchOpts.executablePath = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  }

  const browser = await chromium.launch(launchOpts);
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  await page.goto('file://' + absInput, { waitUntil: 'networkidle' });
  // 额外等待，确保字体和 CSS 动画稳定
  await page.waitForTimeout(500);

  // 截取第一个 <section> 元素（封面/卡片主体），如果没有则截全页
  const section = await page.$('section[data-vds-role]');
  if (section) {
    await section.screenshot({ path: absOutput, omitBackground: false });
  } else {
    await page.screenshot({ path: absOutput, fullPage: false, omitBackground: false });
  }

  await browser.close();
  console.log('PNG: ' + absOutput);
}

main().catch(err => {
  console.error('截图失败:', err.message);
  process.exit(1);
});
