import os
import time
import subprocess
import tempfile
import shutil
from PIL import Image
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Method 1: Selenium-based screenshot capture with tab support
class SeleniumMethod:
    def __init__(self):
        self.name = "Method 1: Selenium Screenshot Capture"
        self.description = """
        **Features:**
        - Uses Selenium WebDriver with Edge browser
        - Captures screenshots of each page and tab
        - Supports interactive tab navigation
        - Creates PDF from multiple screenshots
        - Better for complex interactive content

        **Advantages:**
        - Handles dynamic content well
        - Captures tabs separately
        - Good for debugging (visual screenshots)
        - Works with JavaScript-heavy pages

        **Disadvantages:**
        - Larger file sizes (image-based PDF)
        - Slower processing
        - Requires browser installation
        - May miss some styling details
        """

    def wait_for_visible(self, driver, by, selector, timeout=5):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, selector))
            )
        except TimeoutException:
            return None

    def capture_screenshots_with_tabs(self, driver, page_num, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        screenshots = []

        # Capture full page screenshot
        page_shot = os.path.join(output_dir, f"page_{page_num:02d}_full.png")
        driver.save_screenshot(page_shot)
        screenshots.append(page_shot)

        # Find and capture tab screenshots
        tab_selectors = [
            "a[role=\'tab\']",
            ".nav-tabs .nav-link",
            ".tabset-pills .nav-link",
            ".panel-tabset .nav-link",
            "[data-bs-toggle=\'tab\']",
            "[data-toggle=\'tab\']"
        ]

        all_tabs = []
        for selector in tab_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                visible_tabs = [el for el in elements if el.is_displayed()]
                if visible_tabs:
                    all_tabs = visible_tabs
                    break
            except:
                continue

        # Click each tab and capture screenshot
        for i, tab in enumerate(all_tabs):
            try:
                driver.execute_script("arguments[0].click();", tab)
                time.sleep(0.5)
                tab_name = tab.text.strip().replace(" ", "_").replace("/", "_") or f"{i + 1}"
                filename = os.path.join(output_dir, f"page_{page_num:02d}_tab_{i + 1}_{tab_name}.png")
                driver.save_screenshot(filename)
                screenshots.append(filename)
            except Exception:
                continue

        return screenshots

    def click_next_page(self, driver):
        try:
            next_btn = driver.find_element(By.XPATH, "/html/body/div[3]/aside/button[2]/div")
            if next_btn.is_displayed():
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(1)
                return True
        except NoSuchElementException:
            pass
        return False

    def create_pdf_from_images(self, image_folder, output_path):
        images = sorted([
            os.path.join(image_folder, f)
            for f in os.listdir(image_folder)
            if f.lower().endswith(".png")
        ])
        if not images:
            return False

        try:
            first_image = Image.open(images[0]).convert("RGB")
            rest_images = [Image.open(p).convert("RGB") for p in images[1:]]
            first_image.save(output_path, save_all=True, append_images=rest_images, resolution=600)
            return True
        except Exception as e:
            st.error(f"Error creating PDF: {str(e)}")
            return False

    def process_file(self, file_path, output_dir, progress_callback=None):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=2560,1440")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")

        try:
            driver = webdriver.Edge(options=options)
        except Exception:
            # Fallback to Chrome if Edge is not available
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=2560,1440")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-setuid-sandbox")
            driver = webdriver.Chrome(options=chrome_options)

        url = "file://" + os.path.abspath(file_path)
        driver.get(url)

        total_pages = 0
        while True:
            total_pages += 1
            self.capture_screenshots_with_tabs(driver, total_pages, output_dir)

            if progress_callback:
                progress_callback(total_pages)

            if not self.click_next_page(driver):
                break

        driver.quit()

        pdf_path = os.path.join(output_dir, "output.pdf")
        success = self.create_pdf_from_images(output_dir, pdf_path)

        return pdf_path if success else None, total_pages


# Method 2: Puppeteer-based PDF generation
class PuppeteerMethod:
    def __init__(self):
        self.name = "Method 2: Puppeteer PDF Generation"
        self.description = """
                **Features:**
                - Uses Puppeteer (headless Chrome) via Node.js
                - Direct PDF generation with native browser rendering
                - Advanced content scaling and optimization
                - Handles lazy-loaded images and MathJax
                - A3 landscape format with optimized margins

                **Advantages:**
                - Smaller file sizes (native PDF)
                - Better text quality and searchability
                - Faster processing for large documents
                - Superior handling of web fonts and CSS
                - Better print layout optimization

                **Disadvantages:**
                - Requires Node.js and Puppeteer
                - Less visual debugging capability
                - May not handle some complex interactions
                - Single PDF output (no tab separation)
                """

    def process_file(self, file_path, output_dir, progress_callback=None):
        os.makedirs(output_dir, exist_ok=True)

        output_dir_abs = os.path.abspath(output_dir)
        input_abs = os.path.abspath(file_path)
        pdf_abs = os.path.abspath(os.path.join(output_dir_abs, "output.pdf"))
        bot_js_path = os.path.abspath(os.path.join(output_dir_abs, "bot.js"))

        # BURAYI AYNIYLA KOPYALA
        bot_js_content = r'''
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
'''
        with open(bot_js_path, 'w', encoding='utf-8') as f:
            f.write(bot_js_content)

        try:
            result = subprocess.run(
                ['node', bot_js_path, input_abs, pdf_abs],
                capture_output=True,
                text=True
            )

            if progress_callback:
                progress_callback(1)

            if result.returncode == 0 and os.path.exists(pdf_abs):
                return pdf_abs, 1
            else:
                st.error(f"Puppeteer hata çıktı kodu {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
                return None, 0

        except Exception as e:
            st.error(f"Puppeteer çalıştırma hatası: {str(e)}")
            return None, 0


def main():
    st.set_page_config(
        page_title="HTML to PDF Converter - Dual Method",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    st.title("📄 Quarto to PDF Converter - Dual Method")
    st.markdown("Convert your Quarto HTML files to PDF using two different methods with distinct advantages.")

    # Initialize methods
    selenium_method = SeleniumMethod()
    puppeteer_method = PuppeteerMethod()

    st.markdown("---")
    st.markdown("### ⚙️ Choose Conversion Method")

    # Method selection
    selected_method = st.radio(
        "Select a method:",
        options=["Method 1: Selenium", "Method 2: Puppeteer"],
        index=0,
        horizontal=True
    )

    # Display method information
    if selected_method == "Method 1: Selenium":
        current_method = selenium_method
        st.info("**Selenium Method**: Screenshot-based conversion with tab support. Ideal for interactive content.")
    else:
        current_method = puppeteer_method
        st.info(
            "**Puppeteer Method**: Native PDF generation with advanced optimization. Best for high-quality text and smaller files.")

    # Method comparison
    with st.expander("📊 Click here to see a detailed Method Comparison", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Method 1: Selenium Screenshot Capture")
            st.markdown(selenium_method.description)

        with col2:
            st.markdown("### Method 2: Puppeteer PDF Generation")
            st.markdown(puppeteer_method.description)

    st.markdown("---")

    # File upload
    uploaded_files = st.file_uploader(
        "Upload HTML files",
        type=["html"],
        accept_multiple_files=True,
        help="Select one or more HTML files to convert to PDF"
    )

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")

        # Processing button
        if st.button("🚀 Start Processing", type="primary", use_container_width=True):

            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            total_files = len(uploaded_files)
            completed_files = 0

            # Process each file
            for file_idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing file {file_idx + 1}/{total_files}: {uploaded_file.name}")

                # Create temporary directory for this file
                filename_base = os.path.splitext(uploaded_file.name)[0]
                output_dir = os.path.join("output", filename_base)
                os.makedirs(output_dir, exist_ok=True)

                # Save uploaded file
                file_path = os.path.join(output_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Progress callback
                def update_progress(current_page):
                    progress = (completed_files + (current_page / 10)) / total_files
                    progress_bar.progress(min(progress, 1.0))

                # Process file with selected method
                pdf_path, pages_processed = current_method.process_file(
                    file_path, output_dir, update_progress
                )

                completed_files += 1
                progress_bar.progress(completed_files / total_files)

                # Display results
                st.markdown(f"### 📋 Results for `{uploaded_file.name}`")

                if pdf_path and os.path.exists(pdf_path):
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.success(f"✅ Successfully processed with {current_method.name}")

                    with col2:
                        st.metric("Pages Processed", pages_processed)

                    with col3:
                        file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
                        st.metric("File Size", f"{file_size:.2f} MB")

                    # Download button
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label=f"⬇️ Download PDF for `{uploaded_file.name}`",
                            data=pdf_file,
                            file_name=f"{filename_base}.pdf",
                            mime="application/pdf",
                            key=f"download_{uploaded_file.name}_{selected_method}",
                            use_container_width=True
                        )
                else:
                    st.error(f"❌ Failed to process `{uploaded_file.name}`")

                st.markdown("---")

            # Final status
            progress_bar.empty()
            status_text.empty()
            st.balloons()
            st.success(f"🎉 All {total_files} file(s) processed successfully!")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>💡 <strong>Tip:</strong> For interactive content with tabs, use Method 1. For high-quality text and smaller files, use Method 2.</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

