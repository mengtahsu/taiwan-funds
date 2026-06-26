#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣基金「逢低買進」分析工具  ——  2026 版
==============================================================
情境：今天（2026-06-26）台股大跌，想在今天的低點申購 1~2 筆基金。
這支程式用一套「危機日買進」演算法，從近期真實績效挑出最適合今天買的基金。

⚠️  資料來源限制（很重要，請務必看）：
    本機的網路政策（egress policy）封鎖了所有台灣基金資料站
    （moneydj.com / sitca.org.tw / cnyes.com 等都回 403），
    所以「自動抓全台上千檔基金即時淨值」在這個環境做不到。
    下方 fetch_live() 函式是寫好的、指向官方來源的抓取程式碼，
    但在被封鎖的環境會直接報錯——這是環境限制，不是程式錯誤。

    因此 FUNDS 內的資料是「人工從公開績效搜尋到的 2026 年真實月報酬」，
    每一檔都標註了資料日期。涵蓋的是主流大型台股基金，
    不是全部基金。要跑全市場，把你從券商/基富通匯出的 CSV
    丟給 load_csv() 即可，演算法完全相同。

⚠️  投資有風險，過去績效不代表未來。本工具僅供參考，不構成投資建議。
"""

import csv
import json
import sys

DATA_FILE = "funds_data.json"   # 基金資料來源（由 fetch_funds.py 每日更新）


def load_data(path=DATA_FILE):
    """讀取 funds_data.json：演算法與資料分離，資料每天被 CI 更新。"""
    with open(path, encoding="utf-8") as fp:
        d = json.load(fp)
    funds = []
    for f in d["funds"]:
        funds.append({
            "name": f["name"], "type": f.get("type", "Fund"),
            "sector": f.get("sector", ""),
            "m2026": f.get("m2026", [None] * 5),
            "r2w": f.get("r2w"), "r1m": f.get("r1m"),
            "r3m": f.get("r3m"), "r1y": f.get("r1y"),
            "src": f.get("code", "—"),
        })
    return d.get("as_of", "—"), funds


# ──────────────────────────────────────────────────────────────────────────
# 抓即時資料的函式（在本環境因政策封鎖無法執行，保留供其他環境使用）
# ──────────────────────────────────────────────────────────────────────────
def fetch_live(fund_code):
    """從 MoneyDJ 抓單一基金績效。本環境 egress policy 會擋掉，回 403。"""
    import urllib.request
    url = f"https://www.moneydj.com/funddj/yp/yp012000.djhtm?a={fund_code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:   # noqa: 在被封鎖環境會丟例外
        return resp.read().decode("big5", errors="ignore")


def load_csv(path):
    """
    從券商/基富通匯出的 CSV 載入全市場基金，跑同一套演算法。
    預期欄位：name,type,sector,m1,m2,m3,m4,m5,r1m,r3m,r1y
    """
    funds = []
    with open(path, newline="", encoding="utf-8-sig") as fp:
        for row in csv.DictReader(fp):
            def num(k):
                v = row.get(k, "").strip()
                return float(v) if v not in ("", "None", "-") else None
            funds.append({
                "name": row["name"], "type": row.get("type", "Fund"),
                "sector": row.get("sector", ""),
                "m2026": [num("m1"), num("m2"), num("m3"), num("m4"), num("m5")],
                "r2w": num("r2w"), "r1m": num("r1m"),
                "r3m": num("r3m"), "r1y": num("r1y"),
                "src": "CSV import",
            })
    return funds


# ──────────────────────────────────────────────────────────────────────────
# 「危機日逢低買進」演算法（短期加權版）
# ──────────────────────────────────────────────────────────────────────────
# 台股最近很敏感、兩週內就能變天，所以「最近的表現」最重要。
# 大跌日要買的基金，理想條件與權重：
#   1. 短期動能 50%  ← 近2週/近1月，最新最重要（追強勢：最近還在漲的優先）
#   2. 中期趨勢 20%  ← 近3個月，確認不是曇花一現
#   3. 防禦力   20%  ← 最糟單月跌幅，大跌日要能扛
#   4. 穩定度   10%  ← 2026 正報酬月份比例
#
#  ⚠️ 真正的「近2週」基金報酬在被封鎖的資料站後面，這裡 r2w 多半是 None，
#     演算法會自動退回用 r1m（近1月滾動報酬）當短期代理。
#     若你有近2週數字，填進 r2w 即可，它會優先採用。
# ──────────────────────────────────────────────────────────────────────────
W_SHORT, W_TREND, W_DEFENSE, W_STABLE = 0.50, 0.20, 0.20, 0.10


def months(f):
    return [m for m in f["m2026"] if m is not None]


def short_term(f):
    """
    短期動能（最近最重要）：
    優先用近2週 r2w → 沒有退回近1月 r1m → 再沒有用最近一個有效月份。
    回傳 (數值, 來源標籤)。
    """
    if f.get("r2w") is not None:
        return f["r2w"], "近2週"
    if f.get("r1m") is not None:
        return f["r1m"], "近1月"
    ms = months(f)
    return (ms[-1] if ms else 0.0), "上月"


def momentum_3m(f):
    """近3個月動能：優先用滾動 r3m，沒有就用最近3個有效月份複利。"""
    if f["r3m"] is not None:
        return f["r3m"]
    ms = months(f)[-3:]
    r = 1.0
    for m in ms:
        r *= (1 + m / 100)
    return (r - 1) * 100


def worst_month(f):
    """最糟單月（防禦力）。回傳跌幅大小（正數），沒跌過回 0。"""
    ms = months(f)
    w = min(ms) if ms else 0
    return abs(w) if w < 0 else 0.0


def stability(f):
    """2026 正報酬月份比例 0~100。"""
    ms = months(f)
    return (sum(1 for m in ms if m > 0) / len(ms) * 100) if ms else 0


def long_term(f):
    """長線：近1年報酬，沒有就用 2026 至今複利推估。"""
    if f["r1y"] is not None:
        return f["r1y"]
    r = 1.0
    for m in months(f):
        r *= (1 + m / 100)
    return (r - 1) * 100


def norm(v, lo, hi):
    return 50.0 if hi == lo else (v - lo) / (hi - lo) * 100


def score_all(funds):
    metrics = []
    for f in funds:
        st_val, st_lbl = short_term(f)
        metrics.append({
            "f": f,
            "short": st_val, "short_src": st_lbl,
            "mom": momentum_3m(f),
            "def": worst_month(f),
            "stab": stability(f),
        })
    sh_lo, sh_hi = min(m["short"] for m in metrics), max(m["short"] for m in metrics)
    mom_lo, mom_hi = min(m["mom"] for m in metrics), max(m["mom"] for m in metrics)
    def_hi = max(m["def"] for m in metrics)            # 跌幅最大者

    for m in metrics:
        s_short  = norm(m["short"], sh_lo, sh_hi)               * W_SHORT     # 最近表現最重要
        s_def    = (1 - m["def"] / (def_hi + 1)) * 100          * W_DEFENSE   # 跌越少分越高
        s_trend  = norm(m["mom"], mom_lo, mom_hi)               * W_TREND
        s_stable = m["stab"]                                    * W_STABLE
        m["score"] = round(s_short + s_def + s_trend + s_stable, 1)
    metrics.sort(key=lambda x: x["score"], reverse=True)
    return metrics


def main():
    if len(sys.argv) > 1:                      # 可選：python dip_buy_2026.py funds.csv
        as_of, funds = "(CSV)", load_csv(sys.argv[1])
    else:                                       # 預設讀 funds_data.json（每日更新）
        as_of, funds = load_data()

    ranked = score_all(funds)

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   台灣基金「大跌日逢低買進」分析  ·  2026                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  資料基準日：{as_of}   涵蓋 {len(funds)} 檔基金")
    print("  情境：今天台股大跌，要在今天低點申購 1~2 筆")
    print("  ⚠️ 過去績效不代表未來，僅供參考，非投資建議")
    print("  權重：短期動能50% + 中期趨勢20% + 防禦20% + 穩定10%（追強勢動能）")
    print("─" * 70)
    print(f"{'名次':<4}{'基金':<16}{'評分':>6}{'短期動能':>11}{'最糟月':>9}{'近3月':>9}{'穩定':>7}")
    print("─" * 70)
    for i, m in enumerate(ranked, 1):
        f = m["f"]
        defs = f"-{m['def']:.1f}%" if m["def"] > 0 else "未跌"
        short = f"{m['short']:+.1f}%({m['short_src']})"
        print(f"#{i:<3}{f['name']:<16}{m['score']:>6}{short:>13}{defs:>9}{m['mom']:>8.1f}%{m['stab']:>6.0f}%")
    print("─" * 70)

    best = ranked[0]
    print()
    print(f"🏆 今天最推薦：{best['f']['name']}（{best['f']['sector']}）")
    print(f"   評分 {best['score']} ｜ 短期動能 +{best['short']:.1f}%（{best['short_src']}）｜ "
          f"最糟單月 {('-%.1f%%' % best['def']) if best['def'] else '從未下跌'} ｜ "
          f"近3月 +{best['mom']:.0f}%")
    print(f"   理由：最近表現最強又相對抗跌，台股震盪期進場較安心。")
    print()
    print("📋 操作提醒：")
    print("   • 基金以「當日淨值」成交，平日 15:00 前申購才算今天的低點")
    print("   • 怕買在半山腰 → 分 2~3 批，或改定期定額分散時間風險")
    print("   • 避開單日 2 倍槓桿 ETF：大跌時虧損加倍")
    print()

    out = [{
        "rank": i, "name": m["f"]["name"], "sector": m["f"]["sector"],
        "score": m["score"],
        "short_term_pct": round(m["short"], 2), "short_term_basis": m["short_src"],
        "momentum_3m_pct": round(m["mom"], 2),
        "worst_month_pct": round(-m["def"], 2),
        "stability_pct": round(m["stab"], 1), "monthly_2026": m["f"]["m2026"],
        "source": m["f"]["src"],
    } for i, m in enumerate(ranked, 1)]
    with open("dip_buy_scores_2026.json", "w", encoding="utf-8") as fp:
        json.dump({"as_of": as_of, "ranking": out}, fp,
                  ensure_ascii=False, indent=2)
    print("📄 完整結果已存：dip_buy_scores_2026.json")
    print()


if __name__ == "__main__":
    main()
