const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.toString()));
  
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(2000);
  
  const content = await page.content();
  console.log("HTML length:", content.length);
  if (content.includes("Dev Mode")) {
    console.log("Dev banner found. Clicking Client...");
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const clientBtn = btns.find(b => b.textContent.includes('Client'));
      if (clientBtn) clientBtn.click();
    });
    await page.waitForTimeout(2000);
    console.log("URL after click:", page.url());
    console.log("HTML after click:", (await page.content()).substring(0, 500));
  } else {
    console.log("No dev banner found.");
  }
  
  await browser.close();
})();
