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
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 建立資料夾（支持多層）
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# 轉換為安全 slug（保留中文，替換非法檔名字元）
def slugify(text):
    text = text.strip()
    text = requests.utils.unquote(text)
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, '_')
    text = text.strip(' .')
    return text[:50] or '_'

# 去除 URL 中的 fragment
def normalize_url(url):
    p = urlparse(url)
    return urlunparse(p._replace(fragment=''))

# 遞迴收集所有子頁面，並同時處理（邊抓邊存）
def main():
    ensure_dir(OUTPUT_DIR)
    visited = set()
    to_visit = [normalize_url(ROOT_URL)]
    root_path = urlparse(ROOT_URL).path.rstrip('/')

    while to_visit:
        url = normalize_url(to_visit.pop())
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

        # 偵測此頁面應使用哪種分割規則：
        # 第...條 或 一、二、 先出現者擇一
        header_tags = ['h2','h3','h4','h5','p','div']
        pattern_article = re.compile(r'^(?:第\s*.+?\s*條)')
        pattern_list = re.compile(r'^[一二三四五六七八九十]+、')
        header_pattern = None
        # 依元素出現順序判斷
        for tag in header_tags:
            for elem in soup.find_all(tag):
                txt = elem.get_text(strip=True)
                if pattern_article.match(txt):
                    header_pattern = pattern_article
                    break
                if pattern_list.match(txt):
                    header_pattern = pattern_list
                    break
            if header_pattern:
                break
        # 若兩種都未偵測到，則使用預設雙模式
        if not header_pattern:
            header_pattern = re.compile(r'^(?:第\s*.+?\s*條|[一二三四五六七八九十]+、)')

        # 提取所有法條
        articles = []
        for tag in header_tags:
            for elem in soup.find_all(tag):
                title = elem.get_text(strip=True)
                if not header_pattern.match(title):
                    continue
                content_lines = []
                for sib in elem.next_siblings:
                    if hasattr(sib, 'get_text'):
                        txt = sib.get_text(strip=True)
                        if header_pattern.match(txt):
                            break
                        if txt:
                            content_lines.append(txt)
                content = '\n'.join(content_lines)
                articles.append({'title': title, 'content': content})

        if not articles:
            logger.info(f"No articles found on {url}")
        else:
            # 計算資料夾與檔名
            path = urlparse(url).path.rstrip('/')
            rel = path[len(root_path):]
            segments = [requests.utils.unquote(seg) for seg in rel.split('/') if seg]
            dirs = segments[:-1] if segments else []
            last = segments[-1] if segments else 'index'
            dir_slugs = [slugify(d) for d in dirs]
            law_slug = slugify(last)
            dir_path = os.path.join(OUTPUT_DIR, *dir_slugs)
            ensure_dir(dir_path)

            # 單一JSON存整個法規的所有條文
            file_name = f"{law_slug}.json"
            file_path = os.path.join(dir_path, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({'articles': articles}, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved regulation '{last}' with {len(articles)} articles to {file_path}")

        # 發現並加入子頁面
        for a in soup.find_all('a', href=True):
            full = urljoin(ROOT_URL, a['href'])
            norm = normalize_url(full)
            if norm.startswith(ROOT_URL) and norm not in visited:
                to_visit.append(norm)

    logger.info(f"Completed! Pages visited: {len(visited)}")

if __name__ == '__main__':
    main()
