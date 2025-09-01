# Quarto2PDF

Quarto2PDF is a containerized web application for converting Quarto HTML presentations into high-quality PDF documents.  
It uses **Streamlit** for the interface and **Puppeteer** (via Node.js) for rendering and scaling HTML panels into A3 landscape PDF pages with full support for tabsets, MathJax, and images.

---

## Features
- Convert Quarto HTML presentations into **A3 landscape PDFs**  
- Handles **tabbed panels** (`.panel-tabset-tabby`) by rendering all tabs sequentially  
- Supports **MathJax equations** and ensures they are rendered before PDF export  
- Fixes lazy-loaded images (`data-src`, `data-lazy-src`, `role="img"`) so they appear in the final PDF  
- Applies **auto-scaling** to fit each panel neatly onto PDF pages  
- Fully containerized with Docker and easily deployable  

---

## Project Structure
```
├── app.py              # Streamlit frontend
├── main.py             # Backend orchestration logic
├── bot.js              # Puppeteer-based renderer for HTML → PDF
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker image build configuration
├── docker-compose.yml  # Docker Compose service configuration
```
---

## Requirements

### Python
- Python 3.9+  
- Dependencies in `requirements.txt`:
  - streamlit  
  - selenium  
  - Pillow  
  - webdriver-manager  

### Node.js
- Node.js 18+  
- Puppeteer (installed inside Docker image)

### Docker (recommended)
- Docker 20+  
- Docker Compose

---

## Installation & Usage

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/quarto2pdf.git
cd quarto2pdf
```

### 2. Run with Docker Compose
```bash
docker-compose up --build -d
```

The app will be available at:
http://localhost:8504

### 3. Using the Streamlit app

-	Upload your Quarto HTML file	
-	The system will process it using bot.js (Puppeteer)
-  	A properly scaled A3 PDF will be generated for download

## Manual Usage (without Docker)

### Install dependencies
```bash
pip install -r requirements.txt
npm install puppeteer
```

### Run the Streamlit app
```bash
streamlit run app.py --server.port 8504
```

### Direct CLI usage of Puppeteer script
```bash
node bot.js input.html output.pdf
```

## Example
```bash
node bot.js examples/01-Overview.html output.pdf
```
