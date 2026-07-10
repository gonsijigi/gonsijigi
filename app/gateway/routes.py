"""[아키텍처 박스: FastAPI 게이트웨이] 홈 화면 + /ask SSE 스트리밍.
D3: 관심종목 등록·알림함 추가. JWT 인증은 로드맵(보고서 6.4절)."""
import asyncio
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from app.agent import run_agent
from app.gateway import watchlist, nav
from app.gateway.queue import list_notifications
from app.tools.poller import poll_watchlist

router = APIRouter()


@router.get("/notifications")
async def notifications():
    """사용자 알림함 데이터(읽기 전용) — 홈 알림 패널이 주기적으로 폴링해 표시한다.
    HITL 승인 시 deliver()로 쌓인 것과 같은 저장소를 읽는다(신규 로직 없음)."""
    return JSONResponse(list_notifications())


@router.post("/poll")
async def poll():
    """수동 트리거(B) — 관심종목의 새 공시를 1회 감지해 알림 파이프라인에 투입.
    일반 공시는 알림함, 고위험은 검토 큐로(poll_watchlist가 라우팅)."""
    result = await asyncio.to_thread(poll_watchlist)
    return JSONResponse(result)


class Ask(BaseModel):
    user_id: str = "kim_gaemi"
    question: str


@router.post("/ask")
async def ask(body: Ask):
    """답변을 SSE 로 스트리밍 — 사용자가 빈 화면을 기다리지 않게 한다."""
    # 관심종목은 watchlist(파일 저장)에서 읽어 온다 — 고정 상수 제거(D3)
    codes = [it["code"] for it in watchlist.list_items()]
    answer = await asyncio.to_thread(run_agent, body.user_id, body.question, codes)

    async def stream():
        for line in answer.split("\n"):
            yield f"data: {line}\n\n"
            await asyncio.sleep(0.15)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/", response_class=HTMLResponse)
async def home():
    # 사용자 뷰 네비 주입 — HOME_HTML은 일반 문자열이라 f-string 변환 없이 replace
    page = HOME_HTML.replace("</style>", nav.NAV_STYLE + "</style>", 1)
    page = page.replace("<div class=wrap>", "<div class=wrap>" + nav.user_nav("home"), 1)
    return page


HOME_HTML = """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>공시지기</title><style>
body{font-family:'Malgun Gothic',sans-serif;background:#F5F7FA;margin:0;padding:32px;color:#222}
.wrap{max-width:680px;margin:0 auto}h1{color:#1B2A4A;font-size:22px}
#log{background:#fff;border:1px solid #D5DEEA;border-radius:10px;padding:16px;min-height:280px;white-space:pre-wrap;font-size:14px;line-height:1.6}
form{display:flex;gap:8px;margin-top:12px}
input{flex:1;padding:10px;border:1px solid #D5DEEA;border-radius:8px;font-size:14px}
button{background:#1B2A4A;color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:14px;cursor:pointer}
.note{color:#6B7A90;font-size:12px;margin-top:10px}
/* 홈 2단 레이아웃 + 실시간 알림 패널 (색 토큰은 NAV_STYLE의 :root 사용) */
.wrap:has(.home-grid){max-width:960px!important}
.home-head{margin-bottom:22px}
.home-tag{color:var(--muted);font-size:14px;margin:6px 0 0}
.home-grid{display:grid;grid-template-columns:1fr 300px;gap:20px;align-items:start}
.home-main{min-width:0}
.home-aside{background:var(--canvas);border:1px solid var(--line);border-radius:var(--r-card);padding:16px;box-shadow:var(--shadow);position:sticky;top:24px}
.aside-head{display:flex;align-items:center;justify-content:space-between;font-weight:700;color:var(--ink);font-size:15px;margin-bottom:14px}
.live{display:inline-flex;align-items:center;gap:5px;color:var(--accent);font-size:11px;font-weight:700}
.live .dot{width:7px;height:7px;border-radius:50%;background:var(--accent);animation:pulse 1.6s infinite}
@keyframes pulse{0%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.75)}100%{opacity:1;transform:scale(1)}}
#alerts .alert{border:1px solid var(--line);border-radius:12px;padding:12px 13px;margin-bottom:8px;background:var(--canvas);cursor:pointer;transition:border-color .15s}
#alerts .alert:last-child{margin-bottom:0}
#alerts .alert:hover{border-color:var(--accent)}
#alerts .alert.new{animation:pop .6s ease}
@keyframes pop{0%{background:var(--accent-soft);transform:translateY(-4px)}100%{background:var(--canvas);transform:none}}
#alerts .head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
#alerts .co{font-weight:600;color:var(--ink);font-size:13.5px}
#alerts .rn{color:var(--body);font-size:12.5px;margin-top:3px;line-height:1.45}
#alerts .ts{color:var(--muted);font-size:11px;margin-top:7px;font-family:var(--mono)}
#alerts .chev{color:var(--muted);font-size:11px;margin-top:2px;transition:transform .2s;flex:none}
#alerts .alert.open .chev{transform:rotate(180deg)}
#alerts .body{display:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
#alerts .alert.open .body{display:block}
#alerts .body p{margin:0 0 9px;font-size:12px;color:var(--body);line-height:1.55;white-space:pre-wrap}
#alerts .dart-link{display:inline-block;color:var(--accent);font-size:12.5px;font-weight:600;text-decoration:none}
#alerts .dart-link:hover{text-decoration:underline}
.alert-empty{color:var(--muted);font-size:12.5px;text-align:center;padding:22px 6px;white-space:pre-line;line-height:1.6}
.poll-btn{width:100%;margin-bottom:12px;background:var(--soft);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:9px;font-size:13px;font-weight:600;cursor:pointer}
.poll-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--canvas)}
.poll-btn:disabled{opacity:.6;cursor:default}
@media(max-width:760px){.home-grid{grid-template-columns:1fr}.home-aside{position:static}}
@media(prefers-reduced-motion:reduce){.live .dot,#alerts .alert.new{animation:none}}
/* 해석 대기 로딩 팝업 */
#loading{display:none;position:fixed;inset:0;background:rgba(25,31,40,.35);z-index:50;align-items:center;justify-content:center}
#loading.on{display:flex}
#loading .box{background:#fff;border-radius:16px;padding:20px 24px;box-shadow:0 12px 40px rgba(0,0,0,.18);display:flex;gap:12px;align-items:center;font-size:14.5px;color:#191F28;font-weight:600}
#loading .sp{width:22px;height:22px;border-radius:50%;border:3px solid #EAF2FE;border-top-color:#3182F6;animation:spin .8s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}
</style></head><body><div class=wrap>
<div class="home-head">
<h1>공시지기</h1>
<p class="home-tag">공시가 뜨면 원문 근거까지 붙여 알려드려요. 매매 판단은 하지 않습니다.</p>
</div>
<div class="home-grid">
<div class="home-main">
<div id=log>관심 종목: 삼성전자 · 에코프로비엠 · 카카오
예) "오늘 내 종목 공시 뭐 있었어?" / "삼성전자 유상증자 있어?" / "그래서 지금 팔까?"(가드레일 시연)</div>
<form onsubmit="send(event)"><input id=q placeholder="질문을 입력하세요"><button>질문</button></form>
<p class=note>※ 본 서비스의 해석은 정보 제공 목적이며, 투자 판단의 책임은 투자자 본인에게 있습니다.</p>
</div>
<aside class="home-aside">
<div class="aside-head"><span>🔔 알림</span><span class="live"><span class="dot"></span>LIVE</span></div>
<button class="poll-btn" onclick="pollNow()">새 공시 확인</button>
<div id="alerts"></div>
</aside>
</div></div>
<div id="loading"><div class="box"><div class="sp"></div><span>공시 조회·해석 중…</span></div></div>
<script>
async function send(e){e.preventDefault();
const q=document.getElementById('q').value;if(!q)return;
const log=document.getElementById('log');log.textContent='나: '+q+'\\n\\n공시지기: ';
document.getElementById('q').value='';
const ld=document.getElementById('loading');ld.classList.add('on');
try{
const res=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
const rd=res.body.getReader();const dec=new TextDecoder();
while(true){const{done,value}=await rd.read();if(done)break;
for(const line of dec.decode(value).split('\\n')){
if(line.startsWith('data: ')){const t=line.slice(6);
if(t!=='[DONE]'){ld.classList.remove('on');log.textContent+=t+'\\n';}}}}
}finally{ld.classList.remove('on');}}
var _alertN=0;
async function loadAlerts(){
try{const r=await fetch('/notifications');const items=await r.json();renderAlerts(items);}catch(e){}}
function renderAlerts(items){
const box=document.getElementById('alerts');
if(!items||!items.length){box.innerHTML='<div class="alert-empty">아직 도착한 알림이 없어요.\\n승인된 공시가 여기 실시간으로 떠요.</div>';_alertN=0;return;}
const grew=items.length>_alertN;box.innerHTML='';
items.slice().reverse().forEach(function(it,i){
const d=document.createElement('div');d.className='alert'+(grew&&i===0?' new':'');
const co=document.createElement('div');co.className='co';co.textContent=(it.category?'['+it.category+'] ':'')+(it.corp_name||'');
const rn=document.createElement('div');rn.className='rn';rn.textContent=it.report_nm||'';
const ts=document.createElement('div');ts.className='ts';ts.textContent=it.delivered_at||'';
const left=document.createElement('div');left.appendChild(co);left.appendChild(rn);left.appendChild(ts);
const chev=document.createElement('span');chev.className='chev';chev.textContent='▾';
const head=document.createElement('div');head.className='head';head.appendChild(left);head.appendChild(chev);
const body=document.createElement('div');body.className='body';
if(it.interpretation){const p=document.createElement('p');p.textContent=it.interpretation;body.appendChild(p);}
if(it.rcept_no){const a=document.createElement('a');a.className='dart-link';
a.href='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+encodeURIComponent(it.rcept_no);
a.target='_blank';a.rel='noopener';a.textContent='🔗 DART 원문 보기';
a.onclick=function(ev){ev.stopPropagation();};body.appendChild(a);}
d.appendChild(head);d.appendChild(body);
d.onclick=function(){d.classList.toggle('open');};
box.appendChild(d);});
_alertN=items.length;}
async function pollNow(){
const b=document.querySelector('.poll-btn');if(b){b.disabled=true;b.textContent='확인 중…';}
try{await fetch('/poll',{method:'POST'});await loadAlerts();}catch(e){}
if(b){b.disabled=false;b.textContent='새 공시 확인';}}
loadAlerts();setInterval(loadAlerts,5000);
</script></body></html>"""
