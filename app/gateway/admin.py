"""[아키텍처 박스: 컴플라이언스 검토(HITL)] 관리자 화면.
대기 큐 목록 표시 + 승인/반려 버튼 → 승인 시 콘솔 발송 + /admin/ 리다이렉트."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app.gateway.queue import list_queue, pop_by_id

router = APIRouter(prefix="/admin")


@router.get("/", response_class=HTMLResponse)
async def review_queue():
    items = list_queue()
    if not items:
        rows = "<tr><td colspan='5' style='text-align:center;color:#888'>대기 항목 없음</td></tr>"
    else:
        rows = ""
        for it in items:
            keywords = ", ".join(it.get("risk_keywords") or []) or "—"
            dart_link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it['rcept_no']}"
            rows += f"""
            <tr>
              <td>{it['queued_at']}</td>
              <td>{it['corp_name']}</td>
              <td><a href="{dart_link}" target="_blank">{it['report_nm']}</a></td>
              <td><span class="tag">{keywords}</span></td>
              <td>
                <form method="post" action="/admin/approve/{it['id']}" style="display:inline">
                  <button class="btn-approve">승인</button>
                </form>
                <form method="post" action="/admin/reject/{it['id']}" style="display:inline">
                  <button class="btn-reject">반려</button>
                </form>
              </td>
            </tr>"""

    html = f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
<title>공시지기 — 컴플라이언스 검토</title>
<style>
  body{{font-family:'Malgun Gothic',sans-serif;background:#F5F7FA;margin:0;padding:32px;color:#222}}
  h1{{color:#1B2A4A;font-size:20px;margin-bottom:4px}}
  .sub{{color:#6B7A90;font-size:13px;margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  th{{background:#1B2A4A;color:#fff;padding:11px 14px;font-size:13px;text-align:left}}
  td{{padding:11px 14px;font-size:13px;border-bottom:1px solid #E8EDF3;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  a{{color:#1B2A4A}}
  .tag{{background:#FFF3CD;color:#856404;border-radius:4px;padding:2px 7px;font-size:12px}}
  .btn-approve{{background:#1B7A4A;color:#fff;border:0;border-radius:6px;padding:5px 14px;cursor:pointer;font-size:12px;margin-right:4px}}
  .btn-reject{{background:#A0291C;color:#fff;border:0;border-radius:6px;padding:5px 14px;cursor:pointer;font-size:12px}}
  .btn-approve:hover{{background:#155f3a}}.btn-reject:hover{{background:#7d1f16}}
</style></head><body>
<h1>컴플라이언스 검토 큐</h1>
<p class="sub">고위험 공시는 승인 후 알림함으로 발송됩니다. 반려 시 폐기.</p>
<table>
  <thead><tr>
    <th>접수 시각</th><th>회사</th><th>공시 제목</th><th>위험 키워드</th><th>처리</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
</body></html>"""
    return html


@router.post("/approve/{item_id}")
async def approve(item_id: str):
    item = pop_by_id(item_id)
    if item:
        print(f"[HITL 승인] {item['corp_name']} — {item['report_nm']}")
        print(f"[발송]\n{item['card']}")
    else:
        print(f"[HITL 승인] 항목 없음(이미 처리됨): {item_id}")
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/reject/{item_id}")
async def reject(item_id: str):
    item = pop_by_id(item_id)
    if item:
        print(f"[HITL 반려] {item['corp_name']} — {item['report_nm']} → 폐기")
    else:
        print(f"[HITL 반려] 항목 없음(이미 처리됨): {item_id}")
    return RedirectResponse(url="/admin/", status_code=303)
