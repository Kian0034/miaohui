"""检索性能基准：python3 scripts/bench.py [查询词...]"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.search import SearchService  # noqa: E402

DEFAULT_QUERIES = [
    "红色连衣裙跳舞",
    "白色显卡开箱",
    "发票 报销",
    "会议 白板",
    "二维码",
    "可爱 猫",
    "设置界面 截图",
]


def main():
    queries = sys.argv[1:] or DEFAULT_QUERIES
    svc = SearchService()
    # 预热（模型加载不计时）
    svc.search(queries[0])
    print(f"{'query':<24}{'latency_ms':>10}{'results':>9}  breakdown")
    for q in queries:
        r = svc.search(q)
        print(f"{q:<24}{r['latency_ms']:>10}{len(r['results']):>9}  "
              f"{json.dumps(r['breakdown'])}")


if __name__ == "__main__":
    main()
