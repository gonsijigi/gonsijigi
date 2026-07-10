"""[아키텍처 박스: FastAPI 게이트웨이] 관심종목 관리 화면.
현재 관심종목 표시 + 추가/삭제. 단일 사용자(김개미) 전제, 저장은 app.gateway.watchlist.
디자인은 admin.py 와 동일 톤(네이비 #1B2A4A · 배경 #F5F7FA · 흰 카드 + #D5DEEA)."""
from __future__ import annotations
import html
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.gateway import watchlist, nav

router = APIRouter(prefix="/watchlist")


async def _form(request: Request) -> dict:
    """application/x-www-form-urlencoded 본문 파싱 — python-multipart 의존 없이 처리."""
    raw = (await request.body()).decode("utf-8")
    parsed = parse_qs(raw, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}


@router.get("/", response_class=HTMLResponse)
async def watchlist_page():
    items = watchlist.list_items()
    if not items:
        rows = ("<tr><td colspan='3' style='text-align:center;color:#888'>"
                "관심종목이 없습니다. 아래에서 추가하세요.</td></tr>")
    else:
        rows = ""
        for it in items:
            # 회사명은 사용자 입력 — 화면에 넣는 문자열은 전부 escape(XSS 방지)
            code = html.escape(it.get("code", ""))
            name = html.escape(it.get("name", ""))
            rows += f"""
            <tr>
              <td class="code">{code}</td>
              <td>{name}</td>
              <td>
                <form method="post" action="/watchlist/remove" style="display:inline">
                  <input type="hidden" name="code" value="{code}">
                  <button class="btn-remove">삭제</button>
                </form>
              </td>
            </tr>"""

    return f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>공시지기 — 관심종목 관리</title>
<style>
  body{{font-family:'Malgun Gothic',sans-serif;background:#F5F7FA;margin:0;padding:32px;color:#222}}
  .wrap{{max-width:680px;margin:0 auto}}
  h1{{color:#1B2A4A;font-size:20px;margin-bottom:4px}}
  .sub{{color:#6B7A90;font-size:13px;margin-bottom:20px}}
  .sub a{{color:#1B2A4A}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  th{{background:#1B2A4A;color:#fff;padding:11px 14px;font-size:13px;text-align:left}}
  td{{padding:11px 14px;font-size:14px;border-bottom:1px solid #E8EDF3;vertical-align:middle}}
  tr:last-child td{{border-bottom:none}}
  td.code{{font-family:monospace;color:#1B2A4A}}
  .btn-remove{{background:#A0291C;color:#fff;border:0;border-radius:6px;padding:5px 14px;cursor:pointer;font-size:12px}}
  .btn-remove:hover{{background:#7d1f16}}
  .add{{background:#fff;border:1px solid #D5DEEA;border-radius:10px;padding:16px;margin-top:16px;display:flex;gap:8px;align-items:center}}
  .add input{{padding:9px 10px;border:1px solid #D5DEEA;border-radius:8px;font-size:14px}}
  .add input.code{{width:130px}}
  .add input.name{{flex:1}}
  .btn-add{{background:#1B2A4A;color:#fff;border:0;border-radius:6px;padding:9px 18px;cursor:pointer;font-size:14px}}
  .note{{color:#6B7A90;font-size:12px;margin-top:12px}}
  {nav.NAV_STYLE}
</style></head><body><div class="wrap">
{nav.user_nav("watchlist")}
<h1>관심종목 관리</h1>
<p class="sub">등록된 종목의 공시가 홈 대화창에서 조회됩니다. (사용자: 김개미)</p>
<table>
  <thead><tr><th>종목코드</th><th>회사명</th><th>관리</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<form class="add" method="post" action="/watchlist/add">
  <input class="code" name="code" placeholder="종목코드 6자리" maxlength="6" inputmode="numeric" required>
  <input class="name" name="name" placeholder="회사명" required>
  <button class="btn-add">추가</button>
</form>
<p class="note">※ 종목코드는 숫자 6자리(예: 005930). 중복 코드는 무시됩니다.</p>
</div></body></html>"""


@router.post("/add")
async def add(request: Request):
    form = await _form(request)
    watchlist.add_item(form.get("code", ""), form.get("name", ""))
    return RedirectResponse(url="/watchlist/", status_code=303)


@router.post("/remove")
async def remove(request: Request):
    form = await _form(request)
    watchlist.remove_item(form.get("code", ""))
    return RedirectResponse(url="/watchlist/", status_code=303)
