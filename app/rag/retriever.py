"""과거 유사 공시·용어 검색. D2 구현 지점.
TODO(D2): 벡터 검색 + 메타데이터 필터(종목코드·유형·기간).
구현 후 agent/nodes/interpret.py 가 이 함수를 호출해 근거를 컨텍스트에 추가한다."""


def search_similar(disclosure_type: str, top_k: int = 3) -> list[str]:
    return []  # D2 전까지는 빈 근거 — interpret 노드는 공시 원문 요약만으로 동작
