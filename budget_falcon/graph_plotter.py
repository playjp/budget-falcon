import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
from datetime import datetime
import yaml
from matplotlib.font_manager import FontProperties
from typing import Any


# グラフ生成の高速化のための設定
plt.style.use('fast')
plt.rcParams['path.simplify'] = True
plt.rcParams['path.simplify_threshold'] = 1.0
plt.rcParams['agg.path.chunksize'] = 10000

# フォント設定
font_path: str = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Light.ttf")
jp_font_prop = FontProperties(fname=font_path)
title_fontsize: int = 30
label_fontsize: int = 10
tick_fontsize: int = 20
legend_fontsize: int = 20

# Y軸のtopの最小値
y_top_min: float = 0.01

# サービス設定ファイルの読み込み
service_config_path: str = os.path.join(os.path.dirname(__file__), "config", "services.yml")
try:
    with open(service_config_path, 'r', encoding='utf-8') as f:
        config: dict[str, Any] = yaml.safe_load(f)
        SERVICE_LABEL_MAP: dict[str, list[str]] = config['services']
        CATEGORY_COLOR_MAP: dict[str, str] = config['colors']
        OTHERS: str = config['others']['label']
        OTHERS_COLOR: str = config['others']['color']
        OTHERS_HATCH: str = config['others']['hatch']
except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
    raise RuntimeError(f"Failed to load services configuration: {e}") from e

HATCH_PATTERNS: list[str] = ["", "...", "////", "xxxx", "|||", "+++", "\\\\\\\\", "oo", "OO", "**"]


ServiceRecord = tuple[str, str, str, float]  # (date, account_id, service, cost)
Account = tuple[str, str]  # (account_id, account_name)

def _color_hatch_map(
    records_by_account: dict[str, list[ServiceRecord]] = {},
    service_order: list[str] = []
) -> tuple[dict[str, str], dict[str, str]]:
    # サービスごとにカテゴリを集計
    all_services: set[str] = set()
    for recs in records_by_account.values():
        for _, _, service, _ in recs:
            all_services.add(service)
    services: list[str] = sorted(list(all_services))

    # カテゴリごとにサービスをまとめる
    category_services = {}
    for s in services:
        category = SERVICE_LABEL_MAP.get(s, [None, None])[1]
        if category:
            category_services.setdefault(category, []).append(s)
        else:
            category_services.setdefault(None, []).append(s)

    n_hatches = len(HATCH_PATTERNS)
    service_color_map = {}
    service_hatch_map = {}

    # サービスの順序指定があればそれを使う
    service_rank = {}
    if service_order:
        for idx, s in enumerate(service_order):
            service_rank[s] = idx

    # カテゴリがあるサービスはカテゴリ色＋hatchで区別
    for category, svcs in category_services.items():
        # サービス順序指定があればそれで、なければアルファベット順
        if service_order:
            sorted_svcs = sorted(svcs, key=lambda s: service_rank.get(s, len(service_rank)))
        else:
            sorted_svcs = sorted(svcs)
        if category and category in CATEGORY_COLOR_MAP:
            color = CATEGORY_COLOR_MAP[category]
            for idx, s in enumerate(sorted_svcs):
                service_color_map[s] = color
                service_hatch_map[s] = HATCH_PATTERNS[idx % n_hatches]
        else:
            n_svcs = len(sorted_svcs)
            for idx, s in enumerate(sorted_svcs):
                gray = 0.2 + 0.6 * (idx / max(n_svcs - 1, 1))
                service_color_map[s] = (gray, gray, gray)
                service_hatch_map[s] = ""  # 模様なし

    service_color_map[OTHERS] = OTHERS_COLOR
    service_hatch_map[OTHERS] = OTHERS_HATCH
    return service_color_map, service_hatch_map


def plot_graph(
    records: list[ServiceRecord],
    accounts: list[Account],
    output_path: str,
    top_n_services: int = 8
) -> str:
    """
    Creates a stacked bar chart of AWS costs by service for each account.

    Args:
        records: List of (date, account_id, service, cost) records
        accounts: List of (account_id, account_name) pairs
        output_path: Path where the chart image should be saved
        top_n_services: Number of top services to show in the chart (default: 8)

    Returns:
        str: Path to the generated chart image
    """
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["hatch.color"] = "#ffffff"

    account_ids: list[str] = [account[0] for account in accounts]
    account_names: list[str] = [account[1] for account in accounts]

    # アカウントごとにデータ分割
    records_by_account: dict[str, list[ServiceRecord]] = {aid: [] for aid in account_ids}
    for rec in records:
        _, account_id, _, _ = rec
        if account_id in records_by_account:
            records_by_account[account_id].append(rec)

    # サブプロットの行・列数を決定
    n_accounts = len(account_ids)
    if n_accounts <= 3:
        nrows, ncols = n_accounts, 1
    elif n_accounts <= 12:
        nrows = (n_accounts + 1) // 2
        ncols = 2
    else:
        nrows = (n_accounts + 2) // 3
        ncols = 3

    # まず全アカウントのservice_max_dailyを集計し、サービス順序を決める
    # service -> cost(日次の最大値)
    global_service_max_daily: dict[str, float] = defaultdict(float)
    for recs in records_by_account.values():
        tmp_daily: dict[tuple[str, datetime], float] = defaultdict(float)
        for date_str, _, service, cost in recs:
            try:
                date: datetime = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                continue
            tmp_daily[(service, date)] += cost
            global_service_max_daily[service] = max(global_service_max_daily[service], tmp_daily[(service, date)])
    # cost降順でサービスリスト
    global_service_order: list[str] = [k for k, _ in sorted(global_service_max_daily.items(), key=lambda x:x[1], reverse=True)]

    # --- グラフ描画 ---
    # 色と模様の組み合わせでサービスを区別（サービス順序を渡す）
    service_color_map, service_hatch_map = _color_hatch_map(records_by_account, service_order=global_service_order)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8 * ncols, 4 * nrows), sharex=False)
    axes = axes.flatten() if n_accounts > 1 else [axes]

    def get_service_label(s):
        if s == OTHERS:
            return OTHERS
        if s in SERVICE_LABEL_MAP:
            return SERVICE_LABEL_MAP[s][0]
        return s

    legend_handles_dict: dict[str, Any] = {}  # Any is used for matplotlib.patches.Rectangle
    legend_labels_dict: dict[str, str] = {}
    legend_category_dict: dict[str, str | None] = {}  # service -> category
    for idx, account_id in enumerate(account_ids):
        ax = axes[idx]
        # 日付・サービスごとにコストを集計
        cost_dict: dict[datetime, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        service_totals: dict[str, float] = defaultdict(float)
        service_max_daily: dict[str, float] = defaultdict(float)
        dates: set[datetime] = set()
        for date_str, _, service, cost in records_by_account[account_id]:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                continue
            cost_dict[date][service] += cost
            service_totals[service] += cost
            dates.add(date)
            service_max_daily[service] = max(service_max_daily[service], cost_dict[date][service])
        top_services: list[str] = [k for k, _ in sorted(service_max_daily.items(), key=lambda x:x[1], reverse=True)[:top_n_services]]
        services: list[str] = top_services + (
            [OTHERS] if len(service_max_daily) > top_n_services else []
        )
        dates_list: list[datetime] = sorted(list(dates))
        values: dict[str, list[float]] = {s: [] for s in services}
        for d in dates_list:
            others_sum: float = 0
            for s in service_totals:
                v = cost_dict[d].get(s, 0)
                if s in top_services:
                    values[s].append(v)
                else:
                    others_sum += v
            if OTHERS in values:
                values[OTHERS].append(others_sum)
        bottom = [0] * len(dates)
        dates_num = mdates.date2num(dates_list)  # 日付を数値に変換
        # 色割り当てを共通マップから取得
        for s in services:
            bars = ax.bar(
                dates_num,
                values[s],
                bottom=bottom,
                label=s,
                color=service_color_map.get(s, OTHERS_COLOR),
                hatch=service_hatch_map.get(s, OTHERS_HATCH),
            )
            if s not in legend_handles_dict:
                legend_handles_dict[s] = bars[0]
                legend_labels_dict[s] = get_service_label(s)
                # カテゴリ情報も記録
                legend_category_dict[s] = SERVICE_LABEL_MAP.get(s, [None, None])[1]
            bottom = [b + v for b, v in zip(bottom, values[s])]
        account_name = account_names[idx] if idx < len(account_names) else ""
        ax.set_title(f"{account_name} - {account_id}", fontsize=title_fontsize, fontproperties=jp_font_prop)
        ax.set_ylabel("USD", fontsize=label_fontsize, fontproperties=jp_font_prop, rotation=0, ha="right")
        ax.yaxis.set_label_coords(-0.0135, 1)
        ax.tick_params(axis="both", labelsize=tick_fontsize)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(jp_font_prop)
        def format_date_labels(dates):
            labels = []
            for i, d in enumerate(dates):
                # x軸の最初と最後、または月初めの日付の場合
                if i == 0 or i == len(dates) - 1 or d.day == 1:
                    # 月日を2行で表示
                    labels.append(d.strftime("%-d\n%b"))
                else:
                    # 日のみ1行で表示
                    labels.append(d.strftime("%-d"))
            return labels
        ax.set_xticks(dates_num)  # 数値に変換した日付を使用
        ax.set_xticklabels(format_date_labels(dates_list), rotation=0)
        # サブプロットごとのax.legend()は削除

        # Y軸の設定: コストが極端に小さい場合のみ定数でtopを設定
        account_max_cost = max(sum(cost_dict[date].values()) for date in dates)
        if account_max_cost < y_top_min:
            ax.set_ylim(bottom=0, top=y_top_min)
        else:
            ax.set_ylim(bottom=0)  # 最大値は自動設定

    # 不要なサブプロットを非表示
    for i in range(len(account_ids), len(axes)):
        axes[i].set_visible(False)

    # --- 凡例の順序 カテゴリ順→hatch順→カテゴリなし→Others ---
    category_order = list(CATEGORY_COLOR_MAP.keys())
    # サービスをカテゴリごとにまとめる
    category_to_services = {cat: [] for cat in category_order}
    no_category_services = []
    for s in legend_labels_dict:
        cat = legend_category_dict.get(s)
        if cat in category_to_services:
            # hatchパターンのインデックスを取得
            hatch = service_hatch_map.get(s, "")
            try:
                idx = HATCH_PATTERNS.index(hatch)
            except ValueError:
                idx = 0
            category_to_services[cat].append((idx, s))
        elif s != OTHERS:
            no_category_services.append(s)
    # カテゴリ内でhatch順にソート
    legend_keys = []
    for cat in category_order:
        # hatch順→サービス名順
        sorted_svcs = sorted(category_to_services[cat], key=lambda x: (x[0], legend_labels_dict[x[1]]))
        legend_keys += [s for _, s in sorted_svcs]
    # カテゴリなし
    legend_keys += sorted(no_category_services, key=lambda x: legend_labels_dict[x])
    # Othersは最後
    if OTHERS in legend_labels_dict:
        legend_keys.append(OTHERS)

    fig.legend(
        handles=[legend_handles_dict[s] for s in legend_keys],
        labels=[legend_labels_dict[s] for s in legend_keys],
        bbox_to_anchor=(1, 0.5),
        loc="center left",
        borderaxespad=0,
        fontsize=legend_fontsize,
        prop=jp_font_prop,
        frameon=False,
    )
    plt.tight_layout(pad=2.0)
    plt.subplots_adjust(bottom=0.08)
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    return output_path
