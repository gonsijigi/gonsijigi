"""리플레이 치트시트 — 현재 replay_sample.json 기준 '되는 질문/등록 종목' 목록.
발표 아침 prepare_replay.py로 재생성한 뒤 이걸 돌리면 그날의 시연 대본이 나온다.

실행: python scripts/replay_cheatsheet.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.dart import RISK_KEYWORDS
from app.tools.categories import categorize

with open(os.path.join(os.path.dirname(__file__), "..", "data", "replay_sample.json"),
          encoding="utf-8") as f:
    sample = json.load(f)

by_stock: dict[str, list] = {}
for x in sample:
    by_stock.setdefault(x["stock_code"], []).append(x)

print(f"리플레이 샘플 {len(sample)}건 / 종목 {len(by_stock)}개")
print("※ 같은 종목을 다시 물으면 다음 건으로 순환. 서버 재시작 = 처음부터.\n")
print("── 폴링(새 공시 확인) 시연: 아래 종목을 관심종목에 등록 ──")
for code, items in by_stock.items():
    for i, x in enumerate(items, 1):
        risky = [k for k in RISK_KEYWORDS if k in x["report_nm"]]
        cat = categorize(x["report_nm"])
        if risky:
            tag = f"⚠️ 검토 큐행 ({','.join(risky)})"
        elif cat:
            tag = f"알림 직행 [{cat}]"
        else:
            tag = "5종 아님 → 폴링 제외 (대화 질문은 가능)"
        nth = f"{i}번째 폴링/질문" if len(items) > 1 else "1회"
        print(f"  {x['corp_name']}({code}) {nth}: {x['report_nm'][:30].strip()} → {tag}")

print("\n── 대화 시연 질문 (그대로 입력) ──")
for code, items in by_stock.items():
    print(f'  "{items[0]["corp_name"]} 공시 해석해줘"')
print('  "그래서 지금 팔까?"  → 가드레일 거절')
print('  "ㅁㄴㅇㄹ"           → 되묻기(파싱)')
print("\n※ 샘플에 없는 종목(삼성전자 등)은 리플레이에선 '없음+모드 안내'가 정답 — 라이브 모드에서 '최근'으로 물을 것.")
