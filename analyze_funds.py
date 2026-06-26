#!/usr/bin/env python3
"""
台灣基金分析工具
根據 2025H2 歷史績效，用多重指標評分找出最值得買的基金。
注意：過去績效不代表未來表現，投資有風險。
"""

import json
import math

# ── 2025H2 月報酬資料（來源：research-2025h2.html）─────────────────────────
FUNDS = [
    {"name": "施羅德台灣樂活中小基金-A類型",     "type": "Fund", "h2": [6.09, 11.3,  1.25, 10.2,  3.93,  5.68]},
    {"name": "統一大龍印基金",                   "type": "Fund", "h2": [8.37, 15.02, 2.39, 11.25, 1.75,  7.24]},
    {"name": "統一新亞洲科技能源基金",            "type": "Fund", "h2": [10.16,16.75, 4.22, 12.24, 1.04,  5.79]},
    {"name": "復華亞太神龍科技基金",             "type": "Fund", "h2": [7.27,  7.73,  7.71, 16.78,-0.92,  1.6 ]},
    {"name": "復華全球物聯網科技基金",           "type": "Fund", "h2": [7.56,  4.69,  7.52, 15.76, 0.18,  1.84]},
    {"name": "統一中小基金",                     "type": "Fund", "h2": [9.38, 13.23,-0.12, 20.08, 6.64,  1.92]},
    {"name": "群益臺灣加權指數單日正向2倍基金",  "type": "ETF",  "h2": [14.6,  6.1,  14.1,  19.11,-5.33,  8.51]},
    {"name": "國泰臺灣加權指數單日正向2倍基金",  "type": "ETF",  "h2": [15.0,  5.74, 14.05, 19.07,-4.93,  8.46]},
    {"name": "富邦臺灣加權單日正向兩倍基金",     "type": "ETF",  "h2": [14.75, 5.89, 14.02, 19.09,-5.19,  8.52]},
    {"name": "元大台灣50單日正向2倍基金",        "type": "ETF",  "h2": [14.85, 5.88, 14.05, 19.34,-5.12,  8.47]},
    {"name": "復華全球大趨勢基金",               "type": "Fund", "h2": [2.42, -0.67,  5.75,  5.4, -0.53,  0.75]},
    {"name": "復華亞太成長基金",                 "type": "Fund", "h2": [4.1,  10.06,  7.95, 13.12,-1.63,  2.61]},
    {"name": "台新主流基金",                     "type": "Fund", "h2": [11.88,19.9,   1.45,  6.77, 5.17,  8.62]},
    {"name": "統一龍馬基金",                     "type": "Fund", "h2": [8.17, 14.09,  2.58, 16.53, 5.74,  2.89]},
    {"name": "元大新主流基金",                   "type": "Fund", "h2": [11.71,12.62,  3.03, 14.82, 1.72,  6.48]},
    {"name": "摩根新興科技基金-一般型",           "type": "Fund", "h2": [8.72, 13.0,   2.48, 10.61, 2.21,  5.88]},
    {"name": "安聯台灣科技基金",                 "type": "Fund", "h2": [7.41, 12.85,  5.36, 16.34, 7.16, 10.37]},
    {"name": "復華華人世紀基金",                 "type": "Fund", "h2": [7.45, 10.95,  5.96, 13.91,-2.18,  3.45]},
    {"name": "統一全球新科技基金",               "type": "Fund", "h2": [9.09,  8.45,  6.63, 10.95,-0.28,  1.87]},
    {"name": "復華高成長基金",                   "type": "Fund", "h2": [10.34,14.71,  1.33, 16.76, 3.77,  6.98]},
    {"name": "元大大中華TMT基金",                "type": "Fund", "h2": [9.47,  6.63,  9.49, 11.6,  0.05,  1.87]},
    {"name": "元大多多基金",                     "type": "Fund", "h2": [6.91, 13.55,  3.95, 16.42, 3.38,  6.59]},
    {"name": "路博邁台灣5G股票基金T累積型",      "type": "Fund", "h2": [10.27,12.87,  6.55, 14.28, 2.92,  5.06]},
    {"name": "安聯台灣大壩基金-G累積型",         "type": "Fund", "h2": [10.81,16.15,  2.2,  14.0,  5.84,  7.04]},
    {"name": "安聯台灣大壩基金-A累積型",         "type": "Fund", "h2": [10.74,16.03,  2.13, 13.9,  5.76,  6.95]},
    {"name": "統一強漢基金",                     "type": "Fund", "h2": [7.62, 13.62,  7.47, -3.15,-5.33,  4.53]},
    {"name": "瀚亞高科技基金",                   "type": "Fund", "h2": [9.46,  8.85,  6.36,  6.97, 0.18,  4.46]},
    {"name": "復華復華基金",                     "type": "Fund", "h2": [11.92,14.51,  0.19, 16.23, 3.85,  6.49]},
    {"name": "統一亞太基金",                     "type": "Fund", "h2": [4.64,  9.94,  2.85, 11.85,-1.8,   5.69]},
    {"name": "野村台灣運籌基金",                 "type": "Fund", "h2": [10.41,18.3,   1.92, 15.77, 4.56,  5.68]},
    {"name": "國泰臺韓科技基金",                 "type": "ETF",  "h2": [8.39,  2.55, 11.78, 19.85,-5.08,  9.54]},
    {"name": "野村中小基金-累積S類型",           "type": "Fund", "h2": [7.82, 15.51,  2.09, 12.52, 7.19,  5.22]},
    {"name": "安聯台灣智慧基金",                 "type": "Fund", "h2": [10.17,16.79,  1.6,  14.67, 3.25,  8.75]},
    {"name": "野村中小基金-累積型",              "type": "Fund", "h2": [7.69, 15.44,  2.0,  12.41, 7.07,  5.13]},
    {"name": "國泰美國費城半導體基金",           "type": "ETF",  "h2": [3.15,  3.59, 12.06, 14.45,-0.75,  0.84]},
    {"name": "野村鴻運基金",                     "type": "Fund", "h2": [10.48,18.28,  2.2,  15.75, 4.39,  5.78]},
    {"name": "統一全天候基金",                   "type": "Fund", "h2": [11.67,14.32,  3.06, 17.29, 3.44,  4.7 ]},
    {"name": "凱基台灣精五門基金A類型",          "type": "Fund", "h2": [12.97,17.74, -0.63, 14.9,  2.69,  6.71]},
    {"name": "野村成長基金",                     "type": "Fund", "h2": [10.88,16.56,  4.7,  13.41, 4.9,   4.43]},
    {"name": "復華全方位基金A類型",              "type": "Fund", "h2": [9.5,  12.88,  0.35, 15.17, 3.9,   6.72]},
    {"name": "元大高科技基金",                   "type": "Fund", "h2": [8.78, 13.7,   4.55, 13.26, 2.08,  9.57]},
    {"name": "復華中小精選基金",                 "type": "Fund", "h2": [9.18, 13.84,  0.46, 14.82, 4.08,  5.38]},
    {"name": "統一大中華中小基金",               "type": "Fund", "h2": [8.62, 15.46,  3.29,  9.87, 0.7,   4.49]},
    {"name": "玉山科技島基金",                   "type": "Fund", "h2": [6.83, 13.69,  5.14, 14.79, 6.42,  5.71]},
    {"name": "台新2000高科技基金-A不配息",       "type": "Fund", "h2": [4.9,  16.6,   0.15,  7.95, 5.05,  7.86]},
    {"name": "新光創新科技基金",                 "type": "Fund", "h2": [8.4,  12.67, -1.02, 17.89, 1.38,  5.67]},
    {"name": "元大卓越基金",                     "type": "Fund", "h2": [8.71, 10.37,  4.72,  9.98, 6.07,  6.49]},
    {"name": "野村優質基金-累積型",              "type": "Fund", "h2": [9.61, 15.31,  4.22,  8.46, 5.62,  1.73]},
    {"name": "第一金電子基金",                   "type": "Fund", "h2": [11.23,13.85,  2.08, 15.71, 2.53,  4.39]},
    {"name": "統一奔騰基金",                     "type": "Fund", "h2": [11.07,14.74,  0.98, 16.13, 4.5,   3.82]},
    {"name": "富邦新台商基金",                   "type": "Fund", "h2": [11.46,16.8,  -0.19, 12.7,  2.14,  4.23]},
    {"name": "復華中國5G通信ETF基金",            "type": "ETF",  "h2": [21.68,42.0,   9.91,  0.52,-1.07, 12.39]},
    {"name": "國泰小龍基金",                     "type": "Fund", "h2": [9.49, 17.76,  1.21, 15.35, 4.14,  3.11]},
    {"name": "玉山高成長基金-A類型",             "type": "Fund", "h2": [8.52,  9.38,  4.48, 12.23, 3.93,  4.72]},
    {"name": "統一黑馬基金",                     "type": "Fund", "h2": [11.84,14.35, -0.14, 16.78, 2.15,  5.23]},
    {"name": "凱基台商天下基金",                 "type": "Fund", "h2": [7.81, 10.94,  3.02, 14.3,  0.97,  5.76]},
    {"name": "統一台灣動力基金-A類型",           "type": "Fund", "h2": [11.52,15.35, -0.35, 16.74, 4.07,  3.07]},
    {"name": "國泰台灣高股息基金-B配息",         "type": "Fund", "h2": [7.85, 13.95,  2.61, 10.87, 2.11,  2.64]},
    {"name": "國泰台灣高股息基金-A不配息",       "type": "Fund", "h2": [7.87, 13.92,  2.63, 10.87, 2.1,   2.65]},
    {"name": "統一大滿貫基金-A類型",             "type": "Fund", "h2": [11.53,12.89, -0.37, 16.57, 3.96,  3.24]},
    {"name": "群益創新科技基金",                 "type": "Fund", "h2": [9.21, 16.43,  2.55, 14.32, 1.52,  5.26]},
    {"name": "野村高科技基金-累積型",            "type": "Fund", "h2": [7.16, 12.4,   1.68, 12.82, 4.1,   9.54]},
    {"name": "復華亞太平衡基金",                 "type": "Fund", "h2": [5.19,  3.82,  6.06,  7.9,  1.83,  4.91]},
    {"name": "兆豐臺灣藍籌30ETF基金",           "type": "ETF",  "h2": [8.84,  3.53,  7.31,  9.5, -1.52,  4.86]},
    {"name": "元大台灣高股息優質龍頭基金A不配息","type": "Fund", "h2": [3.96,  3.29,  6.67,  3.74,-0.37,  5.96]},
    {"name": "富邦歐亞絲路多重資產型基金A不配息","type": "Fund", "h2": [4.35, 15.38,  6.34, 11.42,-6.6,   5.16]},
    {"name": "群益亞太新趨勢平衡基金",           "type": "Fund", "h2": [1.32, 10.4,   5.25,  7.57,-1.68,  2.16]},
    {"name": "第一金中概平衡基金",               "type": "Fund", "h2": [8.15, 14.07,  1.79, 12.09, 2.14,  4.84]},
    {"name": "路博邁5G股票基金T累積型",          "type": "Fund", "h2": [7.24,  9.04, 12.03,  7.88,-3.1,  -1.83]},
    {"name": "統一全球智聯網AIoT基金",           "type": "Fund", "h2": [5.69, 10.25,  1.98, 13.86, 0.14,  4.34]},
    {"name": "富邦AI智能新趨勢多重資產型基金-A類型","type":"Fund","h2": [7.88,  4.72,  6.97, 16.62,-1.26,  0.97]},
    {"name": "復華中小精選基金",                 "type": "Fund", "h2": [9.18, 13.84,  0.46, 14.82, 4.08,  5.38]},
    {"name": "統一大中華中小基金",               "type": "Fund", "h2": [8.62, 15.46,  3.29,  9.87, 0.7,   4.49]},
    {"name": "街口標普高盛布蘭特原油ER單日正向2倍指數期貨基金","type":"Fund","h2": [20.36,-9.09,-3.74,-2.62,-5.57,-4.27]},
    {"name": "第一金亞洲科技基金",               "type": "Fund", "h2": [2.11,  5.02, 10.2,  15.67,-4.49,  6.4 ]},
]

# 去除重複
seen = set()
FUNDS_UNIQUE = []
for f in FUNDS:
    if f["name"] not in seen:
        seen.add(f["name"])
        FUNDS_UNIQUE.append(f)
FUNDS = FUNDS_UNIQUE


def cumulative_return(monthly):
    """計算複利累計報酬"""
    r = 1.0
    for m in monthly:
        r *= (1 + m / 100)
    return (r - 1) * 100


def avg_return(monthly):
    return sum(monthly) / len(monthly)


def stddev(monthly):
    avg = avg_return(monthly)
    variance = sum((m - avg) ** 2 for m in monthly) / len(monthly)
    return math.sqrt(variance)


def max_drawdown(monthly):
    """最大單月跌幅（正數表示跌多少）"""
    worst = min(monthly)
    return abs(worst) if worst < 0 else 0


def positive_months(monthly):
    """正報酬月份數"""
    return sum(1 for m in monthly if m > 0)


def momentum_score(monthly):
    """近期動能：最後兩個月的平均"""
    return avg_return(monthly[-2:])


def sharpe_like(monthly):
    """類夏普比：平均月報酬 / 標準差（越高越好）"""
    sd = stddev(monthly)
    if sd == 0:
        return 0
    return avg_return(monthly) / sd


def compute_score(f):
    """
    綜合評分（100分制）：
      - 累計報酬    30%
      - 穩定度      25%（正報酬月份比例）
      - 最大回撤    20%（跌越少越好）
      - 近期動能    15%
      - 夏普比      10%
    """
    m = f["h2"]
    cum  = cumulative_return(m)
    stab = positive_months(m) / len(m) * 100   # 0-100
    mdd  = max_drawdown(m)                       # 越小越好
    mom  = momentum_score(m)
    sh   = sharpe_like(m)

    # 以資料集內最大值做標準化
    return {
        "cum": cum,
        "stab": stab,
        "mdd": mdd,
        "mom": mom,
        "sharpe": sh,
    }


def main():
    # 計算所有指標
    results = []
    for f in FUNDS:
        s = compute_score(f)
        results.append({**f, **s})

    # 找各指標最大/最小值用於正規化
    max_cum  = max(r["cum"]    for r in results)
    min_cum  = min(r["cum"]    for r in results)
    max_mdd  = max(r["mdd"]    for r in results)
    max_mom  = max(r["mom"]    for r in results)
    min_mom  = min(r["mom"]    for r in results)
    max_sh   = max(r["sharpe"] for r in results)
    min_sh   = min(r["sharpe"] for r in results)

    def norm(val, vmin, vmax):
        if vmax == vmin:
            return 50
        return (val - vmin) / (vmax - vmin) * 100

    for r in results:
        score_cum  = norm(r["cum"],    min_cum,  max_cum)   * 0.30
        score_stab = r["stab"]                              * 0.25
        score_mdd  = (1 - r["mdd"] / (max_mdd + 1)) * 100  * 0.20
        score_mom  = norm(r["mom"],    min_mom,  max_mom)   * 0.15
        score_sh   = norm(r["sharpe"], min_sh,   max_sh)    * 0.10
        r["total_score"] = score_cum + score_stab + score_mdd + score_mom + score_sh

    results.sort(key=lambda x: x["total_score"], reverse=True)

    # ── 輸出 ──────────────────────────────────────────────────────────────────
    MONTHS = ["7月", "8月", "9月", "10月", "11月", "12月"]
    SEP = "─" * 68

    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║       台灣基金綜合評分排行榜（2025 下半年）       ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print("  ⚠️  過去績效不代表未來表現，投資前請自行判斷風險。")
    print()

    # ── TOP 10 ────────────────────────────────────────────────────────────────
    print(f"{'排名':<4} {'基金名稱':<30} {'類型':<5} {'評分':>5}  {'累計':>7}  {'穩定':>4}  {'動能':>5}  {'最大跌幅':>6}")
    print(SEP)
    for i, r in enumerate(results[:15], 1):
        tag   = "[ETF]" if r["type"] == "ETF" else "[基金]"
        stab  = f"{r['stab']:.0f}%"
        cum   = f"+{r['cum']:.1f}%" if r['cum'] >= 0 else f"{r['cum']:.1f}%"
        mom   = f"+{r['mom']:.1f}%" if r['mom'] >= 0 else f"{r['mom']:.1f}%"
        mdd   = f"-{r['mdd']:.1f}%" if r['mdd'] > 0 else "無跌月"
        print(f"#{i:<3} {r['name']:<30} {tag:<6} {r['total_score']:>5.1f}  {cum:>7}  {stab:>4}  {mom:>5}  {mdd:>6}")

    print()
    print("─" * 68)
    print("【 建議買入（保守型）：評分高 且 穩定度 100% 的基金 】")
    print()
    conservative = [r for r in results if r["stab"] == 100]
    for r in conservative[:5]:
        months_str = "  ".join(
            f"{m}:{'+' if v >= 0 else ''}{v:.1f}%"
            for m, v in zip(MONTHS, r["h2"])
        )
        print(f"  ★ {r['name']} [{r['type']}]")
        print(f"    評分 {r['total_score']:.1f}  累計 +{r['cum']:.1f}%  六個月全正報酬")
        print(f"    {months_str}")
        print()

    print("─" * 68)
    print("【 建議買入（積極型）：評分最高前 5 名 】")
    print()
    for r in results[:5]:
        months_str = "  ".join(
            f"{m}:{'+' if v >= 0 else ''}{v:.1f}%"
            for m, v in zip(MONTHS, r["h2"])
        )
        print(f"  ★ {r['name']} [{r['type']}]")
        print(f"    評分 {r['total_score']:.1f}  累計 +{r['cum']:.1f}%  最大單月跌 -{r['mdd']:.1f}%")
        print(f"    {months_str}")
        print()

    print("─" * 68)
    print("【 避開名單：最大跌幅 > 5% 或 累計報酬最低 】")
    print()
    risky = [r for r in results if r["mdd"] > 5 or r["cum"] < 0]
    for r in sorted(risky, key=lambda x: x["cum"])[:5]:
        print(f"  ✗ {r['name']} 累計 {r['cum']:.1f}%  最大跌 -{r['mdd']:.1f}%")
    print()

    # ── 儲存 JSON 結果 ─────────────────────────────────────────────────────────
    out = []
    for r in results:
        out.append({
            "rank": results.index(r) + 1,
            "name": r["name"],
            "type": r["type"],
            "score": round(r["total_score"], 2),
            "cumulative_pct": round(r["cum"], 2),
            "stability_pct": round(r["stab"], 1),
            "momentum_pct": round(r["mom"], 2),
            "max_drawdown_pct": round(r["mdd"], 2),
            "sharpe_like": round(r["sharpe"], 3),
            "monthly": r["h2"],
        })
    with open("fund_scores.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print("  📄 完整評分已存至 fund_scores.json")
    print()


if __name__ == "__main__":
    main()
