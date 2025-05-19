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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def slugify(text):
    text = text.strip()
    text = requests.utils.unquote(text)
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, '_')
    return text.strip(' .')[:50] or '_'

def normalize_url(url):
    p = urlparse(url)
    # 去除 fragment (#…) 以統一 URL
    return urlunparse(p._replace(fragment=''))

def main():
    ensure_dir(OUTPUT_DIR)
    visited = set()
    to_visit = [normalize_url(ROOT_URL)]
    root_path = urlparse(ROOT_URL).path.rstrip('/')

    # 正則：先嘗試「第 ... 條」，若無，再用「一、二、…」
    pattern1 = re.compile(r'^第\s*.+?\s*條')          # e.g. 第 1 條
    pattern2 = re.compile(r'^[一二三四五六七八九十]+、')  # e.g. 一、二、三、

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
        paras = soup.select('p')

        # 先取所有「第 ... 條」
        headings = [p for p in paras if pattern1.match(p.get_text(strip=True))]
        # 若沒有，再取「一、二、…」
        if not headings:
            headings = [p for p in paras if pattern2.match(p.get_text(strip=True))]

        # 取 act 名稱：用 URL 最後一段 path（未 slugify）
        path = urlparse(url).path.rstrip('/')
        rel = path[len(root_path):]
        segments = [requests.utils.unquote(seg) for seg in rel.split('/') if seg]
        last = segments[-1] if segments else 'index'

        articles = []
        seen = set()
        for idx, elem in enumerate(headings):
            raw_title = elem.get_text(strip=True)
            if raw_title in seen:
                continue
            seen.add(raw_title)

            # 蒐集這個標題到下一標題之間的所有文字
            next_h = headings[idx + 1] if idx + 1 < len(headings) else None
            body_lines = []
            for sib in elem.next_siblings:
                if sib == next_h:
                    break
                if hasattr(sib, 'get_text'):
                    txt = sib.get_text(strip=True)
                    if txt:
                        body_lines.append(txt)
            body = '\n'.join(body_lines).strip()

            # 判斷標題格式
            if pattern1.match(raw_title):
                # 「第 ... 條」
                article = raw_title
                content = body
            else:
                # 「一、二、…」格式
                prefix = pattern2.match(raw_title).group()  # 例如 "一、"
                article = prefix
                rest = raw_title[len(prefix):].strip()
                if rest:
                    content = rest + '\n' + body
                else:
                    content = body

            articles.append({
                "act": last,
                "article": article,
                "content": content
            })

        # 輸出 JSON
        if articles:
            dir_slugs = [slugify(d) for d in segments[:-1]]
            dir_path = os.path.join(OUTPUT_DIR, *dir_slugs)
            ensure_dir(dir_path)

            file_name = slugify(last) + '.json'
            file_path = os.path.join(dir_path, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(articles)} articles for act '{last}' → {file_path}")
        else:
            logger.info(f"No articles extracted on {url}")

        # 發現並加入新的子頁面連結
        for a in soup.find_all('a', href=True):
            full = urljoin(ROOT_URL, a['href'])
            norm = normalize_url(full)
            if norm.startswith(ROOT_URL) and norm not in visited:
                to_visit.append(norm)

    logger.info(f"Completed! Pages visited: {len(visited)}")

if __name__ == '__main__':
    main()
