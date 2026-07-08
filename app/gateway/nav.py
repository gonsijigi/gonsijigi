"""공통 상단 네비게이션 — 데모용 뷰 분리(사용자/관리자). 인증이 아니다.
사용자 뷰(/, /watchlist)와 관리자 뷰(/admin/*)가 서로 다른 링크 집합을 노출한다.
진짜 접근 차단(로그인/JWT)은 이번 스프린트 범위 밖 — 로드맵.
색은 기존 토큰(네이비 #1B2A4A · 흰 배경 · #D5DEEA 테두리) 그대로."""
from __future__ import annotations

# 각 페이지 <style> 에 주입하는 공통 CSS
NAV_STYLE = """
  .nav{display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap;align-items:center}
  .nav a{text-decoration:none;font-size:13px;padding:7px 13px;border-radius:8px;
         background:#fff;border:1px solid #D5DEEA;color:#1B2A4A}
  .nav a.active{background:#1B2A4A;color:#fff;border-color:#1B2A4A}
  .nav a:hover{border-color:#1B2A4A}
  .nav .spacer{flex:1}
  .nav a.back{color:#6B7A90;border-style:dashed}
"""

# 사용자 뷰 링크 — admin은 노출하지 않는다
_USER_LINKS = [
    ("home",      "/",           "💬 대화"),
    ("watchlist", "/watchlist/", "⭐ 관심종목"),
]

# 관리자 뷰 링크
_ADMIN_LINKS = [
    ("admin", "/admin/",      "🛡️ 검토 큐"),
    ("inbox", "/admin/inbox", "🔔 알림함"),
]


def _links(links: list, active: str) -> list:
    out = []
    for key, href, label in links:
        cls = ' class="active"' if key == active else ""
        out.append(f'<a href="{href}"{cls}>{label}</a>')
    return out


def user_nav(active: str = "") -> str:
    """사용자 뷰 네비 — 대화 · 관심종목만."""
    return '<nav class="nav">' + "".join(_links(_USER_LINKS, active)) + "</nav>"


def admin_nav(active: str = "") -> str:
    """관리자 뷰 네비 — 검토 큐 · 알림함 + 사용자 화면으로 돌아가는 링크."""
    inner = _links(_ADMIN_LINKS, active)
    inner.append('<span class="spacer"></span>')
    inner.append('<a class="back" href="/">← 사용자 화면</a>')
    return '<nav class="nav">' + "".join(inner) + "</nav>"
