// bot.js — robust Quarto HTML to PDF A3 landscape
// Usage: node bot.js input.html output.pdf

const puppeteer = require("puppeteer");
const path = require("path");
const fs = require("fs");

const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
  console.error("Usage: node bot.js input.html output.pdf");
  process.exit(1);
}

const withTimeout = (p, ms, label) =>
  Promise.race([
    p,
    new Promise((_, rej) =>
      setTimeout(() => rej(new Error(`[TIMEOUT ${ms}ms] ${label}`)), ms)
    ),
  ]);

const delay = ms => new Promise(res => setTimeout(res, ms));

(async () => {
  const inAbs = path.resolve(inputFile);
  const outAbs = path.resolve(outputFile);
  if (!fs.existsSync(inAbs)) {
    console.error(`Input not found: ${inAbs}`);
    process.exit(1);
  }

  const executablePath =
    process.env.PUPPETEER_EXECUTABLE_PATH ||
    process.env.CHROME_EXECUTABLE_PATH ||
    "/usr/bin/chromium";

  console.log("[1/9] Launching Chromium…");
  const browser = await puppeteer.launch({
    headless: "new",
    executablePath,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--no-zygote",
      "--single-process",
      "--allow-file-access-from-files",
      "--enable-local-file-accesses",
      "--disable-web-security"
    ]
  });

  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(0);
    page.setDefaultNavigationTimeout(0);

    console.log("[2/9] Set viewport A3 landscape…");
    await page.setViewport({ width: 1587, height: 1123 });

    const fileUrl = `file:${inAbs}`;
    console.log(`[3/9] Goto DOMContentLoaded: ${fileUrl}`);
    await withTimeout(
      page.goto(fileUrl, { waitUntil: "domcontentloaded", timeout: 0 }),
      120000,
      "page.goto(domcontentloaded)"
    );

    console.log("[4/9] Wait for fonts (best effort) …");
    await withTimeout(
      page.evaluate(() => (document.fonts ? document.fonts.ready : Promise.resolve())),
      15000,
      "document.fonts.ready"
    ).catch(() => {});

    console.log("[5/9] Click through tabsets…");
    await withTimeout(
      page.evaluate(async () => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        const selectors = [
          "a[role='tab']",
          ".nav-tabs .nav-link",
          ".tabset-pills .nav-link",
          ".panel-tabset .nav-link",
          "[data-bs-toggle='tab']",
          "[data-toggle='tab']"
        ];
        let clicked = 0;
        for (const sel of selectors) {
          const nodes = Array.from(document.querySelectorAll(sel));
          for (const el of nodes) {
            try { el.click(); clicked++; await sleep(300); } catch {}
          }
          if (clicked > 0) break;
        }
      }),
      15000,
      "click tabsets"
    ).catch(() => {});

    console.log("[6/9] Normalize lazy images and ensure visibility…");
    await page.evaluate(() => {
      document.querySelectorAll("img").forEach(img => {
        const ds = img.getAttribute("data-src") || img.getAttribute("data-lazy-src");
        if (ds && !img.getAttribute("src")) img.setAttribute("src", ds);
        img.style.display = "block";
        img.style.visibility = "visible";
        img.style.opacity = "1";
        img.style.height = "auto";
        img.style.maxWidth = "100%";
        img.style.objectFit = "contain";
      });
    });

    console.log("[7/9] Wait all images with onerror fallback …");
    await withTimeout(
      page.evaluate(async () => {
        const imgs = Array.from(document.images);
        await Promise.all(
          imgs.map(img =>
            img.complete
              ? Promise.resolve()
              : new Promise(res => { img.onload = img.onerror = () => res(); })
          )
        );
      }),
      45000,
      "images load"
    ).catch(() => {});

    console.log("[8/9] MathJax typeset best effort …");
    await withTimeout(
      page.evaluate(async () => {
        try {
          if (window.MathJax && typeof MathJax.typesetPromise === "function") {
            await MathJax.typesetPromise();
          }
        } catch {}
      }),
      15000,
      "MathJax typeset"
    ).catch(() => {});

    console.log("[9/9] Inject print scale and paginate…");
    await page.evaluate(() => {
      const pxPerMm = 3.78;
      const targetWpx = Math.floor((420 - 16 - 16) * pxPerMm);
      const targetHpx = Math.floor((297 - 8 - 8) * pxPerMm);

      const style = document.createElement("style");
      style.textContent = `
        @media print {
          * { box-sizing: border-box !important; }
          html, body { margin: 0 !important; padding: 10px !important; font-size: 8px !important; line-height: 1.3 !important; }
          li { font-size: 8px !important; }
          img { max-width: 100% !important; object-fit: contain !important; page-break-inside: avoid !important; }
          table { font-size: 8px !important; width: 100% !important; page-break-inside: avoid !important; table-layout: fixed !important; }
          td, th { padding: 2px 4px !important; font-size: 8px !important; word-wrap: break-word !important; }
          pre, code { font-size: 7px !important; white-space: pre-wrap !important; word-break: break-word !important; page-break-inside: avoid !important; }
          .panel-tabset-tabby [role="tabpanel"] { page-break-after: always !important; page-break-inside: avoid !important; margin-bottom: 10px !important; }
          h1, h2, h3, h4, h5, h6 { page-break-after: avoid !important; margin-top: 10px !important; margin-bottom: 5px !important; }
        }`;
      document.head.appendChild(style);

      const scaleBlock = el => {
        const w = el.scrollWidth || el.clientWidth || 1;
        const h = el.scrollHeight || el.clientHeight || 1;
        let s = Math.min(targetWpx / w, targetHpx / h, 1);
        s = Math.max(s, 0.5);
        el.style.transformOrigin = "top left";
        el.style.transform = `scale(${s})`;
        el.style.width = `${100 / s}%`;
        el.style.pageBreakAfter = "always";
        el.style.marginBottom = "20px";
        el.style.overflow = "hidden";
      };

      const panels = document.querySelectorAll('[role="tabpanel"]');
      if (panels.length) {
        panels.forEach(p => { try { p.style.display="block"; p.style.visibility="visible"; scaleBlock(p); } catch {} });
      } else {
        const cont = document.querySelectorAll("main, .content, .container, section");
        cont.forEach(c => { try {
          const w = c.scrollWidth || 1, h = c.scrollHeight || 1;
          let s = Math.min(targetWpx / w, targetHpx / h, 1);
          s = Math.max(s, 0.5);
          if (s < 1) { c.style.transformOrigin = "top left"; c.style.transform = `scale(${s})`; c.style.width = `${100 / s}%`; c.style.overflow="hidden"; }
        } catch {} });
      }

      document.body.style.padding = "10px";
      document.body.style.margin = "0";
      document.body.style.boxSizing = "border-box";
    });

    await delay(800);
    await page.evaluate(async () => {
      await new Promise(resolve => {
        let total = 0, step = 200;
        const t = setInterval(() => {
          const h = document.body.scrollHeight;
          window.scrollBy(0, step);
          total += step;
          if (total >= h - window.innerHeight) { clearInterval(t); resolve(); }
        }, 40);
      });
      window.scrollTo(0, 0);
    });

    console.log("[PDF] Creating file…");
    await withTimeout(
      page.pdf({
        path: outAbs,
        format: "A3",
        landscape: true,
        printBackground: true,
        margin: { top: "8mm", bottom: "8mm", left: "8mm", right: "8mm" },
        preferCSSPageSize: false,
        displayHeaderFooter: false
      }),
      60000,
      "page.pdf"
    );

    console.log(`PDF başarıyla oluşturuldu: ${outAbs}`);
    await browser.close();
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();