"""공통 상단 네비게이션 — 데모용 뷰 분리(사용자/관리자). 인증이 아니다.
사용자 뷰(/, /watchlist)와 관리자 뷰(/admin/*)가 서로 다른 링크 집합을 노출한다.
진짜 접근 차단(로그인/JWT)은 이번 스프린트 범위 밖 — 로드맵.
색은 기존 토큰(네이비 #1B2A4A · 흰 배경 · #D5DEEA 테두리) 그대로."""
from __future__ import annotations

# 각 페이지 <style> 의 '맨 끝'에 주입되는 공통 테마 = 디자인 시스템.
# 나중에 선언돼 페이지의 옛 인라인 CSS를 덮어쓴다(HTML/로직은 그대로, 외형만 교체).
# 방향: 토스풍 클린 — 흰 캔버스 · 단일 블루 액센트(인색하게) · 필드형 입력 · 부드러운 카드 ·
#       한글 시스템폰트(Apple SD Gothic Neo/Pretendard). 위험/삭제는 빨강 '텍스트/외곽선'만, 채우기 금지.
NAV_STYLE = """
  :root{
    --bg:#F7F8FA; --canvas:#FFFFFF; --soft:#F2F4F6;
    --ink:#191F28; --body:#4E5968; --muted:#8B95A1; --line:#E8EBEE;
    --accent:#3182F6; --accent-active:#1B64DA; --accent-soft:#EAF2FE;
    --danger:#E5484D; --danger-soft:#FDECEE;
    --warn-ink:#9A6A00; --warn-soft:#FFF4DE;
    --r-card:16px; --r-btn:12px; --r-field:12px;
    --shadow:0 1px 2px rgba(17,24,39,.04), 0 8px 24px rgba(17,24,39,.05);
    --sans:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Malgun Gothic",sans-serif;
    --mono:"SF Mono","JetBrains Mono",ui-monospace,Menlo,monospace;
  }
  *{box-sizing:border-box}
  body{font-family:var(--sans)!important;background:var(--bg)!important;color:var(--body)!important;
       margin:0!important;padding:40px 24px!important;line-height:1.5;-webkit-font-smoothing:antialiased;
       letter-spacing:-.01em}
  .wrap{max-width:720px!important;margin:0 auto!important}
  h1{color:var(--ink)!important;font-size:23px!important;font-weight:700!important;
     letter-spacing:-.03em;margin:0 0 6px!important;line-height:1.3}
  .sub{color:var(--muted)!important;font-size:13.5px!important;margin:0 0 24px!important}
  .sub a{color:var(--accent)!important;text-decoration:none}
  .note{color:var(--muted)!important;font-size:12.5px!important;margin-top:14px!important}
  a{color:var(--accent)}

  /* 네비 — 세그먼트 칩 */
  .nav{display:flex;gap:6px;margin-bottom:22px;flex-wrap:wrap;align-items:center}
  .nav a{text-decoration:none;font-size:13.5px;font-weight:600;padding:8px 14px;border-radius:10px;
         background:var(--canvas);border:1px solid var(--line);color:var(--body);transition:.15s}
  .nav a.active{background:var(--ink);color:#fff;border-color:var(--ink)}
  .nav a:hover{border-color:var(--muted);color:var(--ink)}
  .nav a.active:hover{color:#fff}
  .nav .spacer{flex:1}
  .nav a.back{color:var(--muted);border-style:dashed;font-weight:500}

  /* 버튼 — 기본=프라이머리 블루, 위험/삭제=빨강 고스트 */
  button{font-family:var(--sans);background:var(--accent);color:#fff;border:0;border-radius:var(--r-btn);
         padding:11px 18px;font-size:14.5px;font-weight:600;cursor:pointer;transition:.15s;letter-spacing:-.01em}
  button:hover{background:var(--accent-active)}
  button:active{transform:translateY(1px)}
  .btn-approve,.btn-add{background:var(--accent);color:#fff}
  .btn-approve:hover,.btn-add:hover{background:var(--accent-active)}
  .btn-reject,.btn-remove{background:var(--canvas);color:var(--danger);border:1px solid var(--danger-soft)}
  .btn-reject:hover,.btn-remove:hover{background:var(--danger-soft)}

  /* 대화 화면(홈) */
  #log{background:var(--canvas)!important;border:1px solid var(--line)!important;border-radius:var(--r-card)!important;
       padding:20px!important;min-height:300px!important;white-space:pre-wrap;font-size:14.5px!important;
       line-height:1.72!important;color:var(--ink)!important;box-shadow:var(--shadow)}
  .wrap>form{display:flex!important;gap:8px!important;margin-top:14px!important}
  #q{flex:1!important;background:var(--soft)!important;border:1px solid transparent!important;
     border-radius:var(--r-field)!important;padding:12px 14px!important;font-size:15px!important;
     color:var(--ink)!important;font-family:var(--sans);transition:.15s}
  #q:focus{outline:none;background:var(--canvas)!important;border-color:var(--accent)!important}

  /* 표(검토 큐 · 관심종목) — 라이트 헤더, 카드형 */
  .table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:var(--r-card)}
  table{width:100%!important;border-collapse:separate!important;border-spacing:0!important;
        background:var(--canvas)!important;border:1px solid var(--line)!important;border-radius:var(--r-card)!important;
        overflow:hidden!important;box-shadow:var(--shadow)!important}
  th{background:#FBFCFD!important;color:var(--muted)!important;padding:13px 16px!important;font-size:12px!important;
     font-weight:600!important;text-align:left!important;letter-spacing:0;border-bottom:1px solid var(--line)!important}
  td{padding:14px 16px!important;font-size:14px!important;color:var(--body)!important;
     border-bottom:1px solid var(--line)!important;vertical-align:top}
  tr:last-child td{border-bottom:none!important}
  td.code,.code{font-family:var(--mono)!important;color:var(--ink)!important;font-size:13px!important}
  table a{color:var(--accent)!important;text-decoration:none}

  /* 위험 키워드 태그 — 빨강 텍스트/틴트 (채우기 아님) */
  .tag{display:inline-block;background:var(--danger-soft)!important;color:var(--danger)!important;
       border-radius:999px!important;padding:3px 11px!important;font-size:12px!important;font-weight:600}
  .interp{margin:0 0 6px!important;line-height:1.62!important;color:var(--ink)!important}
  details summary{cursor:pointer;color:var(--muted)!important;font-size:12px!important}
  .card-pre{background:var(--soft)!important;border-radius:10px!important;padding:12px!important;font-size:12px!important;
            white-space:pre-wrap;margin:8px 0 0!important;color:var(--body)!important;
            font-family:var(--mono);max-width:380px}

  /* 알림함 카드 */
  .card{background:var(--canvas)!important;border:1px solid var(--line)!important;border-radius:var(--r-card)!important;
        padding:18px 20px!important;margin-bottom:12px!important;box-shadow:var(--shadow)!important}
  .card .meta,.meta{color:var(--muted)!important;font-size:12px!important;margin-bottom:8px!important}
  .card pre{white-space:pre-wrap;font-size:13.5px!important;line-height:1.62!important;color:var(--ink)!important;
            margin:0!important;font-family:var(--sans)}

  /* 관심종목 추가 폼 */
  .add{background:var(--canvas)!important;border:1px solid var(--line)!important;border-radius:var(--r-card)!important;
       padding:16px!important;margin-top:16px!important;display:flex;gap:8px;align-items:center;box-shadow:var(--shadow)}
  .add input{background:var(--soft)!important;border:1px solid transparent!important;border-radius:var(--r-field)!important;
             padding:11px 12px!important;font-size:14px!important;color:var(--ink)!important;font-family:var(--sans)}
  .add input:focus{outline:none;background:var(--canvas)!important;border-color:var(--accent)!important}
  .add input.code{width:150px!important}
  .add input.name{flex:1!important}

  :focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  @media (max-width:640px){
    body{padding:24px 16px!important}
    .add{flex-wrap:wrap}
    .add input.code,.add input.name{width:100%!important;flex:none!important}
    /* 검토 큐 표는 좁은 화면에서 세로로 뭉개지지 않게 최소폭 유지 + 가로 스크롤 */
    .table-scroll table{min-width:660px!important}
    .table-scroll th,.table-scroll td{white-space:nowrap!important}
    .table-scroll td .interp,.table-scroll td .card-pre{white-space:normal!important}
  }
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
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
