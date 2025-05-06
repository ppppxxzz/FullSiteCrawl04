import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import re
import json
import os
import logging

# 根 URL：所有子頁面位於此路徑下
ROOT_URL = 'https://sites.google.com/view/police-law-executive-order'
# 輸出根資料夾
OUTPUT_DIR = 'laws_json'
# 日誌檔案名稱
LOG_FILE = 'scrape.log'

# 設定 Logging：同時輸出到檔案與終端
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 建立資料夾（支援多層）
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# 生成安全 slug（保留中文，替換非法檔名字元）
def slugify(text):
    text = text.strip()
    text = requests.utils.unquote(text)
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, '_')
    text = text.strip(' .')
    return text[:50] or '_'

# 去除 URL fragment
def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=''))

# 主程式：遞迴一邊爬取一邊儲存每個法規為一個 JSON 檔
def main():
    ensure_dir(OUTPUT_DIR)
    visited = set()
    to_visit = [normalize_url(ROOT_URL)]
    root_path = urlparse(ROOT_URL).path.rstrip('/')

    while to_visit:
        raw_url = to_visit.pop()
        url = normalize_url(raw_url)
        if url in visited:
            continue
        visited.add(url)
        logger.info(f"Fetching page: {url}")

        try:
            resp = requests.get(url)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 只在主要內容區塊抓取，避免匹配到導覽列或其他重複元素
        container = soup.find('div', id='sites-canvas-main')
        if not container:
            # 如果找不到指定容器，就使用整個 soup
            container = soup

        # 擷取條文標題與內容
        header_pattern = re.compile(r'^(?:第\s*.+?\s*條|[一二三四五六七八九十]+、)')
        articles = []
        # 只搜尋 heading 標籤作為標題
        for header in container.find_all(['h2', 'h3', 'h4', 'h5']):
            title = header.get_text(strip=True)
            if not header_pattern.match(title):
                continue
            # 從標題的同層兄弟節點收集內容，直到下一個標題
            content_lines = []
            for sib in header.next_siblings:
                if not hasattr(sib, 'get_text'):
                    continue
                text = sib.get_text(strip=True)
                if header_pattern.match(text):
                    break
                if text:
                    content_lines.append(text)
            content = '\n'.join(content_lines)
            articles.append({'title': title, 'content': content})

        # 如果找到法條，則輸出單一 JSON 檔
        if articles:
            # 計算路徑層級與檔名
            path = urlparse(url).path.rstrip('/')
            rel = path[len(root_path):]
            segments = [requests.utils.unquote(seg) for seg in rel.split('/') if seg]
            law_name = segments[-1] if segments else 'index'
            law_slug = slugify(law_name)
            dirs = segments[:-1]
            dir_slugs = [slugify(d) for d in dirs]
            dir_path = os.path.join(OUTPUT_DIR, *dir_slugs)
            ensure_dir(dir_path)

            structured = []
            for art in articles:
                article_slug = slugify(art['title'])
                doc_id = f"{law_slug}_{article_slug}"
                text = f"{art['title']}\n{art['content']}" if art['content'] else art['title']
                metadata = {
                    'law': law_name,
                    'article': art['title'],
                    'path': segments
                }
                structured.append({'id': doc_id, 'text': text, 'metadata': metadata})

            file_path = os.path.join(dir_path, f"{law_slug}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({'articles': structured}, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved regulation '{law_name}' with {len(structured)} articles to {file_path}")
        else:
            logger.info(f"No articles found on {url}, skipping.")

        # 探索並加入子頁面 URL
        for a in soup.find_all('a', href=True):
            full = urljoin(ROOT_URL, a['href'])
            norm = normalize_url(full)
            if norm.startswith(ROOT_URL) and norm not in visited:
                to_visit.append(norm)

    logger.info(f"Completed! Pages visited: {len(visited)}")

if __name__ == '__main__':
    main()
