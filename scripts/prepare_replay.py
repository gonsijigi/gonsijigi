"""오늘(또는 지정일) DART 공시를 내려받아 data/replay_sample.json 으로 저장.

사용법:
  python scripts/prepare_replay.py                 # 오늘 날짜
  python scripts/prepare_replay.py --date 20260707 # 특정 날짜
"""
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

CORP_MAP_PATH = ROOT / "data" / "corp_map.json"
OUTPUT_PATH = ROOT / "data" / "replay_sample.json"


def main():
    parser = argparse.ArgumentParser(description="DART 공시 → replay_sample.json")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"),
                        help="조회 날짜 (YYYYMMDD, 기본=오늘)")
    args = parser.parse_args()

    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        print("오류: .env 에 DART_API_KEY 가 필요합니다.")
        sys.exit(1)

    if not CORP_MAP_PATH.exists():
        print("오류: data/corp_map.json 이 없습니다. build_corp_map() 을 먼저 실행하세요.")
        sys.exit(1)

    with open(CORP_MAP_PATH, encoding="utf-8") as f:
        corp_map = json.load(f)
    # corp_map 은 {종목코드: 고유번호} — 역전환 필요
    code_to_stock = {v: k for k, v in corp_map.items()}

    import requests
    # 전체 공시 조회 (corp_code 미지정 → 전 종목)
    params = {
        "crtfc_key": api_key,
        "bgn_de": args.date,
        "end_de": args.date,
        "page_count": 100,
    }
    print(f"DART 공시 조회 중 … (날짜: {args.date})")
    resp = requests.get("https://opendart.fss.or.kr/api/list.json",
                        params=params, timeout=15)
    data = resp.json()

    if data.get("status") != "000":
        print(f"DART 응답 오류: {data.get('status')} — {data.get('message')}")
        sys.exit(1)

    items = data.get("list", [])
    # 데모용 큐레이션: 6자리 종목코드만(관심종목 등록 가능) + (종목,제목) 중복 제거
    # + 고위험은 전부, 일반은 MAX_NORMAL건까지 (알림 화면이 지저분해지지 않게)
    import re
    RISK = ["유상증자", "감사의견", "거래정지", "불성실공시", "상장폐지", "회생절차"]
    MAX_NORMAL = 12
    seen, risky, normal = set(), [], []
    for it in items:
        stock_code = code_to_stock.get(it.get("corp_code"), "")
        if not re.match(r"^\d{6}$", stock_code):
            continue
        key = (stock_code, it["report_nm"])
        if key in seen:
            continue
        seen.add(key)
        row = {
            "stock_code": stock_code,
            "corp_name": it["corp_name"],
            "report_nm": it["report_nm"],
            "rcept_no": it["rcept_no"],
            "rcept_dt": it["rcept_dt"],
            "summary": f"{it['rcept_dt']} 접수 — 상세는 원문 링크 참고",
        }
        (risky if any(k in it["report_nm"] for k in RISK) else normal).append(row)
    result = risky + normal[:MAX_NORMAL]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {OUTPUT_PATH}  (고위험 {len(risky)} + 일반 {min(len(normal), MAX_NORMAL)} = {len(result)}건)")
    print("데모 등록 후보 (⚠️=고위험 → HITL 시연 가능):")
    for r in result[:8]:
        mark = "⚠️ " if any(k in r["report_nm"] for k in RISK) else "   "
        print(f"  {mark}{r['stock_code']}  {r['corp_name']} — {r['report_nm'][:38]}")


if __name__ == "__main__":
    main()
