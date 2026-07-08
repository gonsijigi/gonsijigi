"""[아키텍처 박스: FastAPI 게이트웨이] 홈 화면 + /ask SSE 스트리밍.
D3: 관심종목 등록·알림함 추가. JWT 인증은 로드맵(보고서 6.4절)."""
import asyncio
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.agent import run_agent
from app.gateway import watchlist, nav

router = APIRouter()


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
<title>공시지기 MVP</title><style>
body{font-family:'Malgun Gothic',sans-serif;background:#F5F7FA;margin:0;padding:32px;color:#222}
.wrap{max-width:680px;margin:0 auto}h1{color:#1B2A4A;font-size:22px}
#log{background:#fff;border:1px solid #D5DEEA;border-radius:10px;padding:16px;min-height:280px;white-space:pre-wrap;font-size:14px;line-height:1.6}
form{display:flex;gap:8px;margin-top:12px}
input{flex:1;padding:10px;border:1px solid #D5DEEA;border-radius:8px;font-size:14px}
button{background:#1B2A4A;color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:14px;cursor:pointer}
.note{color:#6B7A90;font-size:12px;margin-top:10px}</style></head><body><div class=wrap>
<h1>공시지기 — 개인투자자용 공시 알림·해석 Agent (MVP)</h1>
<div id=log>관심 종목: 삼성전자 · 에코프로비엠 · 카카오
예) "오늘 내 종목 공시 뭐 있었어?" / "그래서 지금 팔까?"(가드레일 시연)</div>
<form onsubmit="send(event)"><input id=q placeholder="질문을 입력하세요"><button>질문</button></form>
<p class=note>※ 본 서비스의 해석은 정보 제공 목적이며, 투자 판단의 책임은 투자자 본인에게 있습니다.</p></div>
<script>
async function send(e){e.preventDefault();
const q=document.getElementById('q').value;if(!q)return;
const log=document.getElementById('log');log.textContent='나: '+q+'\\n\\n공시지기: ';
document.getElementById('q').value='';
const res=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
const rd=res.body.getReader();const dec=new TextDecoder();
while(true){const{done,value}=await rd.read();if(done)break;
for(const line of dec.decode(value).split('\\n')){
if(line.startsWith('data: ')){const t=line.slice(6);
if(t!=='[DONE]')log.textContent+=t+'\\n';}}}}
</script></body></html>"""
