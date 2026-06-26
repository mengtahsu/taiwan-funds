#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_funds.py  ——  抓取市場前 N 強台股基金的近期報酬，寫進 funds_data.json
==============================================================================
這支程式負責「每天抓最新資料」。它 **不是** 設計在 Claude 沙盒裡跑——
沙盒的網路政策封鎖了所有基金資料站（MoneyDJ / TWSE / 公會 等都回 403）。
它要跑在「網路開放」的環境：GitHub Actions runner，或你原本那台每日機器人。

流程：
    抓 MoneyDJ 國內基金績效排行 → 取近3月報酬前 N 名 → 解析各檔月報酬/滾動報酬
    → 驗證資料量足夠 → 覆寫 funds_data.json

安全機制（很重要）：
    若抓取失敗、或解析出的基金數 < MIN_FUNDS，**不會覆寫** funds_data.json，
    並以非 0 結束碼退出，讓 CI 變紅、提醒你資料源可能改版了。
    這樣網頁永遠不會被半殘 / 空白資料蓋掉。

⚠️ 誠實聲明：下方解析邏輯是在「無法連到該網站」的環境寫的（沙盒被擋），
   MoneyDJ 頁面結構若與預期不同，第一次在 CI 跑時需要依實際 HTML 微調 PARSE 區塊。
"""

import json
import re
import sys
import datetime
import urllib.request

# ── 設定 ─────────────────────────────────────────────────────────────────────
TOP_N      = 100          # 取前幾強
MIN_FUNDS  = 20           # 少於這個數量就視為抓取失敗，不覆寫
OUT_FILE   = "funds_data.json"
RANK_URL   = ("https://www.moneydj.com/funddj/yb/yp080000.djhtm"
              "?ex=ALL&et=08")          # 國內股票型基金，依近3月報酬排序
PERF_URL   = "https://www.moneydj.com/funddj/yp/yp012000.djhtm?a={code}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    # MoneyDJ 多為 big5；解碼失敗就退回 utf-8
    for enc in ("big5", "utf-8"):
        try:
            return raw.decode(enc, errors="strict")
        except UnicodeDecodeError:
            continue
    return raw.decode("big5", errors="ignore")


def parse_ranking(html):
    """
    從排行頁解析 (基金代碼, 名稱)。回傳前 TOP_N 檔。
    ── 需在 CI 依實際 HTML 驗證的區塊 ──
    MoneyDJ 連結格式通常為 yp010000.djhtm?a=ACDD04 之類，名稱在連結文字。
    """
    pairs = re.findall(
        r'yp0?1?0000\.djhtm\?a=([A-Za-z0-9]+)[^>]*>([^<]+)</a>', html)
    seen, out = set(), []
    for code, name in pairs:
        code = code.upper()
        name = name.strip()
        if code in seen or not name:
            continue
        seen.add(code)
        out.append({"code": code, "name": name})
        if len(out) >= TOP_N:
            break
    return out


def parse_perf(html):
    """
    從單檔績效頁抓近1月 / 近3月 / 近1年報酬與最近月報酬。
    ── 需在 CI 依實際 HTML 驗證的區塊 ──
    這裡用寬鬆的數字擷取；解析不到就回 None，演算法端會自動退階。
    """
    def grab(label):
        m = re.search(label + r'[^%\-\d]{0,20}(-?\d+\.?\d*)', html)
        return float(m.group(1)) if m else None
    return {
        "r1m": grab("近一月"),
        "r3m": grab("近三月"),
        "r1y": grab("近一年"),
        "sector": "台股",
    }


def main():
    try:
        rank_html = http_get(RANK_URL)
        funds_meta = parse_ranking(rank_html)
    except Exception as e:                       # 連不到 / 被擋
        print(f"[ERROR] 抓排行失敗：{e}", file=sys.stderr)
        sys.exit(2)

    funds = []
    for fm in funds_meta:
        try:
            perf = parse_perf(http_get(PERF_URL.format(code=fm["code"])))
        except Exception:
            perf = {"r1m": None, "r3m": None, "r1y": None, "sector": "台股"}
        funds.append({
            "name": fm["name"], "sector": perf["sector"], "code": fm["code"],
            "m2026": [None] * 5,                 # 月報酬另由月報酬頁補，缺則靠滾動報酬
            "r2w": None, "r1m": perf["r1m"], "r3m": perf["r3m"], "r1y": perf["r1y"],
        })

    # ── 安全閥：資料不足就不覆寫 ──
    usable = [f for f in funds if f["r3m"] is not None or f["r1m"] is not None]
    if len(usable) < MIN_FUNDS:
        print(f"[ERROR] 只解析到 {len(usable)} 檔有效資料（<{MIN_FUNDS}），"
              f"不覆寫 {OUT_FILE}。資料源可能改版了。", file=sys.stderr)
        sys.exit(3)

    out = {
        "as_of": datetime.date.today().isoformat(),
        "note": f"fetch_funds.py 自 MoneyDJ 自動更新，前 {len(funds)} 強台股基金",
        "funds": funds,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print(f"[OK] 已更新 {OUT_FILE}：{len(funds)} 檔基金，基準日 {out['as_of']}")


if __name__ == "__main__":
    main()
