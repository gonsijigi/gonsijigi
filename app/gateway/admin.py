"""[아키텍처 박스: 컴플라이언스 검토(HITL)] 관리자 화면.
대기 큐 목록 표시 + 승인/반려 버튼 → 승인 시 콘솔 발송 + /admin/ 리다이렉트."""
import html
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app.gateway.queue import (list_queue, pop_by_id,
                               deliver, list_notifications)
from app.gateway import nav

router = APIRouter(prefix="/admin")


@router.get("/", response_class=HTMLResponse)
async def review_queue():
    items = list_queue()
    if not items:
        rows = "<tr><td colspan='6' style='text-align:center;color:#888'>대기 항목 없음</td></tr>"
    else:
        rows = ""
        for it in items:
            # DART는 외부 데이터 — 화면에 넣는 문자열은 전부 escape(XSS 방지)
            keywords = html.escape(", ".join(it.get("risk_keywords") or []) or "—")
            queued_at = html.escape(it.get("queued_at", ""))
            corp_name = html.escape(it.get("corp_name", ""))
            report_nm = html.escape(it.get("report_nm", ""))
            item_id = quote(str(it.get("id", "")), safe="")
            dart_link = ("https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
                         + quote(str(it.get("rcept_no", "")), safe=""))
            interpretation = html.escape(it.get("interpretation", ""))
            card = html.escape(it.get("card", ""))
            rows += f"""
            <tr>
              <td>{queued_at}</td>
              <td>{corp_name}</td>
              <td><a href="{dart_link}" target="_blank" rel="noopener">{report_nm}</a></td>
              <td><span class="tag">{keywords}</span></td>
              <td>
                <p class="interp">{interpretation}</p>
                <details>
                  <summary>카드 미리보기</summary>
                  <pre class="card-pre">{card}</pre>
                </details>
              </td>
              <td>
                <form method="post" action="/admin/approve/{item_id}" style="display:inline">
                  <button class="btn-approve">승인</button>
                </form>
                <form method="post" action="/admin/reject/{item_id}" style="display:inline">
                  <button class="btn-reject">반려</button>
                </form>
              </td>
            </tr>"""

    page = f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
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
  .interp{{margin:0 0 6px;line-height:1.5;color:#333}}
  details summary{{cursor:pointer;color:#6B7A90;font-size:12px}}
  .card-pre{{background:#F0F4F8;border-radius:6px;padding:10px;font-size:11px;
             white-space:pre-wrap;margin:6px 0 0;color:#333;max-width:360px}}
  .btn-approve{{background:#1B7A4A;color:#fff;border:0;border-radius:6px;padding:5px 14px;cursor:pointer;font-size:12px;margin-right:4px}}
  .btn-reject{{background:#A0291C;color:#fff;border:0;border-radius:6px;padding:5px 14px;cursor:pointer;font-size:12px}}
  .btn-approve:hover{{background:#155f3a}}.btn-reject:hover{{background:#7d1f16}}
  {nav.NAV_STYLE}
</style></head><body>
{nav.admin_nav("admin")}
<h1>컴플라이언스 검토 큐</h1>
<p class="sub">고위험 공시는 승인 후 알림함으로 발송됩니다. 반려 시 폐기.</p>
<table>
  <thead><tr>
    <th>접수 시각</th><th>회사</th><th>공시 제목</th><th>위험 키워드</th><th>AI 해석 내용</th><th>처리</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
</body></html>"""
    return page


@router.post("/approve/{item_id}")
async def approve(item_id: str):
    item = pop_by_id(item_id)
    if item:
        deliver(item)  # 사용자 알림함(/admin/inbox)에 실제 적재
        print(f"[HITL 승인→발송] {item['corp_name']} — {item['report_nm']}")
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


@router.get("/inbox", response_class=HTMLResponse)
async def user_inbox():
    """사용자 알림함 — HITL 승인된 고위험 공시가 여기로 도착한다(발표 시연용)."""
    notis = list_notifications()
    if not notis:
        cards = "<p style='color:#888'>아직 도착한 알림이 없습니다. 관리자가 승인하면 여기에 표시됩니다.</p>"
    else:
        cards = ""
        for n in reversed(notis):  # 최신 알림이 위로
            cards += f"""
            <div class="card">
              <div class="meta">{html.escape(n['delivered_at'])} · {html.escape(n['corp_name'])}</div>
              <pre>{html.escape(n['card'])}</pre>
            </div>"""
    return f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
<title>공시지기 — 내 알림함</title>
<style>
  body{{font-family:'Malgun Gothic',sans-serif;background:#F5F7FA;margin:0;padding:32px;color:#222}}
  h1{{color:#1B2A4A;font-size:20px;margin-bottom:16px}}
  .card{{background:#fff;border:1px solid #D5DEEA;border-radius:10px;padding:16px;
         margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
  .meta{{color:#6B7A90;font-size:12px;margin-bottom:8px}}
  pre{{white-space:pre-wrap;font-size:13px;line-height:1.6;margin:0}}
  {nav.NAV_STYLE}
</style></head><body>
{nav.admin_nav("inbox")}
<h1>내 알림함 (승인 완료 발송분)</h1>
{cards}
</body></html>"""
