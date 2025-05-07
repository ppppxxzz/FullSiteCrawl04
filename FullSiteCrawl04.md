# 法規爬蟲腳本

本專案提供一支用於爬取 Google Sites 上「警察法規執行命令」（Police Law Executive Order）網站的 Python 腳本，並將每篇法條以 JSON 格式輸出。

## 功能

* 遞迴抓取指定根網址下所有子頁面
* 解析網頁中「第 X 條」或「一、二、三...」等法條標題
* 收集標題與內容，結構化後輸出為 JSON
* 支援中文檔名 slug 化、目錄結構自動建立
* 記錄抓取過程與錯誤至日誌檔

## 環境需求

* Python 3.6+
* 套件：

  ```text
  requests
  beautifulsoup4
  ```

## 安裝

1. 將專案複製到本機：

   ```bash
   git clone <你的專案網址>
   cd <專案資料夾>
   ```
2. 安裝相依套件：

   ```bash
   pip install -r requirements.txt
   ```

## 設定

* `ROOT_URL`：爬取根網址，預設為 `https://sites.google.com/view/police-law-executive-order`
* `OUTPUT_DIR`：JSON 輸出資料夾，預設為 `laws_json`
* `LOG_FILE`：日誌檔名稱，預設為 `scrape.log`

可直接在 `scrape_laws.py`（或 `main.py`）中修改以上參數。

## 使用方式

```bash
python scrape_laws.py
```

執行後將會：

1. 建立輸出資料夾（若不存在）
2. 遞迴爬取所有子頁面
3. 解析法條標題與內容，並輸出 JSON
4. 在終端與 `scrape.log` 顯示執行紀錄

## 日誌說明

* 日誌級別：`INFO` 以上
* 輸出位置：終端與根目錄下的 `scrape.log`

## 輸出結構範例

```bash
laws_json/
├── index.json
├── 子目錄1/
│   └── 法規slug.json
└── 子目錄2/
    └── 另一法規slug.json
```

單一 JSON 檔範例內容：

```json
{
  "articles": [
    {
      "id": "lawslug_article1",
      "text": "第一條\n本條文內容...",
      "metadata": {
        "law": "法規名稱",
        "article": "第一條",
        "path": ["子目錄1", "法規slug"]
      }
    }
    // ...更多條文
  ]
}
```

## 檔案結構

```text
.
├── scrape_laws.py      # 主程式
├── requirements.txt    # 相依套件列表
├── scrape.log          # 執行日誌
└── laws_json/          # 輸出資料夾
```

## 貢獻

歡迎提出 Issue 或 PR，改進功能與錯誤修正。

## 授權

本專案採用 MIT 授權。
