// bot.js
const puppeteer = require("puppeteer");
const path = require("path");

const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
  console.error("Usage: node bot.js input.html output.pdf");
  process.exit(1);
}

(async () => {
  const browser = await puppeteer.launch({
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-web-security",
      "--allow-file-access-from-files"
    ]
  });

  const page = await browser.newPage();

  // A3 landscape boyutları ayarladık
  await page.setViewport({
    width: 1587, // A3 landscape width at 96 DPI
    height: 1123,  // A3 landscape height at 96 DPI
  });

  const fileUrl = `file:${path.resolve(inputFile)}`;

  await page.goto(fileUrl, {
    waitUntil: "networkidle0",
    timeout: 0
  });

  // 1. Sekmeleri sırayla aç (tabset içindekiler)
  await page.evaluate(async () => {
    const delay = ms => new Promise(res => setTimeout(res, ms));
    const tabsets = document.querySelectorAll('.panel-tabset-tabby');
    for (const tabset of tabsets) {
      const tabs = tabset.querySelectorAll('a');
      for (const tab of tabs) {
        tab.click();
        await delay(500);
      }
    }
  });

  // 2. Lazy-load + base64 + role="img" görselleri işleme
  await page.evaluate(() => {
    document.querySelectorAll("img").forEach(img => {
      const dataSrc = img.getAttribute("data-src") || img.getAttribute("data-lazy-src");
      if (dataSrc) {
        img.setAttribute("src", dataSrc);
      }
    });

    const roleImgs = document.querySelectorAll("img[role='img']");
    roleImgs.forEach(img => {
      const dataSrc = img.getAttribute("data-src");
      if (dataSrc && !img.getAttribute("src")) {
        img.setAttribute("src", dataSrc);
      }
    });

    document.querySelectorAll("img").forEach(img => {
      img.style.display = "block";
      img.style.visibility = "visible";
      img.style.opacity = "1";
      img.style.height = "auto";
      img.style.maxWidth = "100%";
      img.style.objectFit = "contain";
    });
  });

  // 3. Tüm görsellerin yüklenmesini bekle
  await page.evaluate(async () => {
    const images = Array.from(document.images);
    await Promise.all(images.map(img => {
      if (img.complete) return Promise.resolve();
      return new Promise(resolve => {
        img.onload = img.onerror = () => resolve();
      });
    }));
  });

  // 4. Sayfanın tamamına scroll yap
  await autoScroll(page);

  // 5. MathJax varsa render tamamlanmasını bekle
  await page.evaluate(async () => {
    if (window.MathJax && MathJax.typesetPromise) {
      await MathJax.typesetPromise();
    }
  });

  // 6. İçeriği sayfalara sığacak şekilde auto-scale et (İyileştirilmiş)
  await page.evaluate(() => {
    // A3 landscape boyutları (mm cinsinden margin dahil)
    const pageWidth = 360; // ~420mm - 16mm margin
    const pageHeight = 255; // ~297mm - 16mm margin

    // CSS ile sayfa kırılmalarını kontrol et
    const style = document.createElement('style');
    style.textContent = `
      @media print {
        * {
          box-sizing: border-box !important;
        }
        
        body {
          margin: 0 !important;
          padding: 10px !important;
          font-size: 8px !important;
          line-height: 1.3 !important;
        }
        
        li {
          font-size: 8px !important;
        }
        
        
        img {
          max-width: 100% !important;
          max-height: 100% !important;
          object-fit: contain !important;
          page-break-inside: avoid !important;
        }
        .slide-logo {
          max-width: 5% !important;
          max-height: 5% !important;
          object-fit: contain !important;
          page-break-inside: avoid !important;
        }
        
        .header-logo {
          max-width: 7% !important;
          max-height: 7% !important;
          object-fit: contain !important;
          page-break-inside: avoid !important;
        }
        
        table {
          font-size: 8px !important;
          width: 100% !important;
          page-break-inside: avoid !important;
          table-layout: fixed !important;
        }
        
        td, th {
          padding: 2px 4px !important;
          font-size: 8px !important;
          word-wrap: break-word !important;
        }
        
        .panel-tabset-tabby [role="tabpanel"] {
          page-break-after: always !important;
          page-break-inside: avoid !important;
          margin-bottom: 10px !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
          page-break-after: avoid !important;
          margin-top: 10px !important;
          margin-bottom: 5px !important;
        }
        
        pre, code {
          font-size: 7px !important;
          white-space: pre-wrap !important;
          word-break: break-word !important;
          page-break-inside: avoid !important;
          max-width: 100% !important;
          overflow-wrap: break-word !important;
        }
      }
    `;
    document.head.appendChild(style);

    // Her tabpanel için ayrı scaling
    const panels = document.querySelectorAll('[role="tabpanel"]');
    panels.forEach((panel, index) => {
      // Panel'in gerçek boyutunu ölç
      const rect = panel.getBoundingClientRect();
      const panelWidth = panel.scrollWidth;
      const panelHeight = panel.scrollHeight;

      console.log(`Panel ${index}: ${panelWidth}x${panelHeight}`);

      // Scaling faktörlerini hesapla
      let scaleX = pageWidth / panelWidth;
      let scaleY = pageHeight / panelHeight;

      // En küçük scale faktörünü kullan (aspect ratio korunur)
      let scale = Math.min(scaleX, scaleY, 1);

      // Minimum scale sınırı (çok küçültmeyi engelle)
      scale = Math.max(scale, 0.5); // 0.4'ten 0.3'e düşürdük

      // Transform uygula
      panel.style.transformOrigin = "top left";
      panel.style.transform = `scale(${scale})`;
      panel.style.width = `${100 / scale}%`;
      panel.style.height = "auto";
      panel.style.pageBreakAfter = "always";
      panel.style.marginBottom = "20px";
      panel.style.overflow = "hidden";

      console.log(`Panel ${index} scaled to: ${scale}`);
    });

    // Eğer tabpanel yoksa, ana container'ları scale et
    if (panels.length === 0) {
      const containers = document.querySelectorAll('main, .content, .container, section');
      containers.forEach((container, index) => {
        const containerWidth = container.scrollWidth;
        const containerHeight = container.scrollHeight;

        let scaleX = pageWidth / containerWidth;
        let scaleY = pageHeight / containerHeight;
        let scale = Math.min(scaleX, scaleY, 1);
        scale = Math.max(scale, 0.5); // 0.4'ten 0.3'e düşürdük

        if (scale < 1) {
          container.style.transformOrigin = "top left";
          container.style.transform = `scale(${scale})`;
          container.style.width = `${100 / scale}%`;
          container.style.overflow = "hidden";
        }
      });
    }

    // Genel body styling
    document.body.style.padding = "10px";
    document.body.style.margin = "0";
    document.body.style.boxSizing = "border-box";
  });

  // 7. Scaling işleminden sonra render için bekleme
  await new Promise(resolve => setTimeout(resolve, 2000));

  // 8. PDF çıktısı al
  await page.pdf({
    path: outputFile,
    format: "A3", // A4'ten A3'e çıkardık
    printBackground: true,
    landscape: true,
    margin: {
      top: "8mm",  // Margin'leri küçülttük
      bottom: "8mm",
      left: "8mm",
      right: "8mm"
    },
    preferCSSPageSize: false,
    displayHeaderFooter: false
  });

  console.log(`PDF başarıyla oluşturuldu: ${outputFile}`);
  await browser.close();
})();

// Sayfa sonuna kadar scroll eden yardımcı fonksiyon
async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise(resolve => {
      let totalHeight = 0;
      const distance = 100;
      const timer = setInterval(() => {
        const scrollHeight = document.body.scrollHeight;
        window.scrollBy(0, distance);
        totalHeight += distance;
        if (totalHeight >= scrollHeight - window.innerHeight) {
          clearInterval(timer);
          resolve();
        }
      }, 100);
    });
  });

  // Scroll işleminden sonra yukarı çık
  await page.evaluate(() => {
    window.scrollTo(0, 0);
  });
}