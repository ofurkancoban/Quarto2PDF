import os
import time
from PIL import Image
import streamlit as st
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_visible(driver, by, selector, timeout=5):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
    except TimeoutException:
        return None

def capture_screenshots_with_tabs(driver, page_num, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    screenshots = []

    page_shot = os.path.join(output_dir, f"page_{page_num:02d}_full.png")
    driver.save_screenshot(page_shot)
    screenshots.append(page_shot)

    tab_selectors = [
        "a[role='tab']",
        ".nav-tabs .nav-link",
        ".tabset-pills .nav-link",
        ".panel-tabset .nav-link",
        "[data-bs-toggle='tab']",
        "[data-toggle='tab']"
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

    for i, tab in enumerate(all_tabs):
        try:
            driver.execute_script("arguments[0].click();", tab)
            time.sleep(0.5)
            tab_name = tab.text.strip().replace(" ", "_").replace("/", "_") or f"{i+1}"
            filename = os.path.join(output_dir, f"page_{page_num:02d}_tab_{i+1}_{tab_name}.png")
            driver.save_screenshot(filename)
            screenshots.append(filename)
        except Exception:
            continue

    return screenshots

def click_next_page(driver):
    try:
        next_btn = driver.find_element(By.XPATH, "/html/body/div[3]/aside/button[2]/div")
        if next_btn.is_displayed():
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(1)
            return True
    except NoSuchElementException:
        pass
    return False

def create_pdf_from_images(image_folder="screenshots", output_path="output.pdf"):
    images = sorted([
        os.path.join(image_folder, f)
        for f in os.listdir(image_folder)
        if f.lower().endswith(".png")
    ])
    if not images:
        return
    first_image = Image.open(images[0]).convert("RGB")
    rest_images = [Image.open(p).convert("RGB") for p in images[1:]]
    first_image.save(output_path, save_all=True, append_images=rest_images, resolution=600)

def process_html_file(driver, url, output_dir, progress_callback=None, current_page=0):
    driver.get(url)

    total_pages = 0
    while True:
        total_pages += 1
        capture_screenshots_with_tabs(driver, total_pages, output_dir)

        if progress_callback:
            progress_callback(current_page + total_pages)

        if not click_next_page(driver):
            break

    pdf_path = os.path.join(output_dir, "output.pdf")
    create_pdf_from_images(output_dir, pdf_path)
    return total_pages

def run_streamlit_ui():
    st.set_page_config(page_title="HTML to PDF Converter", layout="centered")
    st.title("📄 HTML to PDF Screenshot Capturer")
    st.markdown("Convert your Quarto HTML files into high-resolution PDFs with tab support.")
    st.markdown("Upload multiple HTML files and get individual downloadable PDF files.")
    st.markdown("---")

    uploaded_files = st.file_uploader("Upload HTML files", type=["html"], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Start Processing"):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=2560,1440")
        driver = webdriver.Edge(options=options)

        progress_bar = st.progress(0)
        completed_pages = 0
        estimated_pages_per_file = 10
        total_pages_all_files = estimated_pages_per_file * len(uploaded_files)

        for uploaded_file in uploaded_files:
            filename_base = os.path.splitext(uploaded_file.name)[0]
            output_dir = os.path.join("output", filename_base)
            os.makedirs(output_dir, exist_ok=True)

            file_path = os.path.join(output_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.markdown(f"---\n#### 🔍 Processing: `{uploaded_file.name}`")
            url = "file://" + os.path.abspath(file_path)

            def update_progress(current):
                progress_bar.progress(min(current / total_pages_all_files, 1.0))

            pages_processed = process_html_file(driver, url, output_dir, update_progress, completed_pages)
            completed_pages += pages_processed

            pdf_path = os.path.join(output_dir, "output.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"⬇️ Download PDF for `{uploaded_file.name}`",
                        data=pdf_file,
                        file_name=f"{filename_base}.pdf",
                        mime="application/pdf",
                        key=f"download_{uploaded_file.name}",
                        use_container_width=True
                    )

        driver.quit()
        progress_bar.empty()
        st.success(f"✅ All files processed! Total pages: {completed_pages}")

if __name__ == "__main__":
    run_streamlit_ui()