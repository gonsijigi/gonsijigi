"""[아키텍처 박스: 데이터 저장소] 적재 파이프라인.
DART 실제 공시 원문을 수집 → 청킹 → 임베딩 → pgvector 저장.

실행: python -m app.rag.ingest [--clear]
"""
import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

import OpenDartReader

# 호환 shim: OpenDartReader 0.1.6은 pandas 1.x의 DataFrame.append()를 쓰는데
# pandas 2.0에서 이 메서드가 삭제됨 → list() 호출이 전부 실패한다.
# 삭제된 append를 pd.concat 기반으로 되살려 적재만 정상 동작하게 한다(라이브러리 우회).
import pandas as _pd
if not hasattr(_pd.DataFrame, "append"):
    def _df_append(self, other, ignore_index=False, **_kw):
        if isinstance(other, dict):
            other = _pd.DataFrame([other])
        elif isinstance(other, _pd.Series):
            other = other.to_frame().T
        return _pd.concat([self, other], ignore_index=ignore_index)
    _pd.DataFrame.append = _df_append

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVectorStore

from app.rag.db import get_engine
from app.tools.dart import get_document_text

TABLE_NAME = "disclosure_corpus"
VECTOR_SIZE = 1024  # BGE-M3

KEYWORDS = ["유상증자", "자기주식", "타법인"]
TARGET_PER_KEYWORD = 15


def collect_disclosures(dart: OpenDartReader) -> list[dict]:
    """최근 6개월 공시에서 키워드별 10~15건씩 수집."""
    today = datetime.now()
    # 3개월씩 2구간
    ranges = [
        ((today - timedelta(days=180)).strftime("%Y%m%d"),
         (today - timedelta(days=91)).strftime("%Y%m%d")),
        ((today - timedelta(days=90)).strftime("%Y%m%d"),
         today.strftime("%Y%m%d")),
    ]

    collected: dict[str, list[dict]] = {kw: [] for kw in KEYWORDS}

    for bgn, end in ranges:
        for kind in ["B", ""]:  # 주요사항보고 우선, 안 걸리면 전체
            try:
                listing = dart.list(start=bgn, end=end, kind=kind if kind else None)
            except Exception as e:
                print(f"  [경고] dart.list({bgn}~{end}, kind={kind!r}) 실패: {e}")
                continue
            if listing is None or (hasattr(listing, 'empty') and listing.empty):
                continue

            for _, row in listing.iterrows():
                report_nm = row.get("report_nm", "")
                for kw in KEYWORDS:
                    if kw in report_nm and len(collected[kw]) < TARGET_PER_KEYWORD:
                        # 중복 접수번호 방지
                        existing_nos = {d["rcept_no"] for d in collected[kw]}
                        rcept_no = row["rcept_no"]
                        if rcept_no not in existing_nos:
                            collected[kw].append({
                                "corp_name": row.get("corp_name", ""),
                                "report_nm": report_nm,
                                "rcept_no": rcept_no,
                                "rcept_dt": row.get("rcept_dt", ""),
                            })

            # 이 kind로 충분하면 다음 kind 시도 안 함
            if all(len(collected[kw]) >= 10 for kw in KEYWORDS):
                break

    print("=== 유형별 확보 건수 ===")
    all_items = []
    for kw in KEYWORDS:
        print(f"  {kw}: {len(collected[kw])}건")
        all_items.extend(collected[kw])

    # 중복 접수번호 제거 (키워드 겹치는 경우)
    seen = set()
    deduped = []
    for item in all_items:
        if item["rcept_no"] not in seen:
            seen.add(item["rcept_no"])
            deduped.append(item)

    print(f"  합계(중복 제거): {len(deduped)}건")
    return deduped


def extract_and_chunk(items: list[dict]) -> list[Document]:
    """원문 추출 → 청킹 → Document 리스트."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150,
    )
    docs: list[Document] = []
    success = 0
    fail = 0

    for i, item in enumerate(items):
        rcept_no = item["rcept_no"]
        print(f"  [{i+1}/{len(items)}] {item['corp_name']} — {item['report_nm']} ({rcept_no})")
        text = get_document_text(rcept_no)
        if not text:
            print(f"    → 원문 추출 실패, 건너뜀")
            fail += 1
            continue
        success += 1

        chunks = splitter.split_text(text)
        for chunk in chunks:
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "corp_name": item["corp_name"],
                    "report_nm": item["report_nm"],
                    "rcept_no": rcept_no,
                    "rcept_dt": item["rcept_dt"],
                },
            ))

    print(f"\n=== 원문 추출 결과: 성공 {success} / 실패 {fail} ===")
    print(f"=== 총 청크 수: {len(docs)} ===")
    return docs


def store_documents(docs: list[Document], clear: bool = False):
    """pgvector에 임베딩·저장."""
    engine = get_engine()

    if clear:
        print("기존 테이블 삭제 후 재생성...")
        try:
            engine.drop_vectorstore_table(TABLE_NAME)
        except Exception:
            pass

    engine.init_vectorstore_table(table_name=TABLE_NAME, vector_size=VECTOR_SIZE)

    emb = OllamaEmbeddings(model="bge-m3")
    store = PGVectorStore.create_sync(
        engine=engine,
        table_name=TABLE_NAME,
        embedding_service=emb,
    )

    BATCH = 20
    for i in range(0, len(docs), BATCH):
        batch = docs[i:i+BATCH]
        store.add_documents(batch)
        print(f"  적재: {min(i+BATCH, len(docs))}/{len(docs)}")

    print("=== 적재 완료 ===")


def main():
    parser = argparse.ArgumentParser(description="DART 공시 → pgvector 적재")
    parser.add_argument("--clear", action="store_true", help="기존 데이터 삭제 후 재적재")
    args = parser.parse_args()

    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        print("오류: .env에 DART_API_KEY가 필요합니다.")
        sys.exit(1)

    dart = OpenDartReader(api_key)

    print("\n[1/3] 공시 목록 수집")
    items = collect_disclosures(dart)
    if not items:
        print("수집된 공시가 없습니다.")
        sys.exit(1)

    print("\n[2/3] 원문 추출 + 청킹")
    docs = extract_and_chunk(items)
    if not docs:
        print("추출된 문서가 없습니다.")
        sys.exit(1)

    print("\n[3/3] pgvector 적재")
    store_documents(docs, clear=args.clear)


if __name__ == "__main__":
    main()
