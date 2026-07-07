"""[MCP 도구] get_price — 시세 조회 (mock, 실서비스: 거래소/증권사 API)."""
from datetime import datetime


def get_price(stock_code: str) -> dict:
    fake = {"005930": 91200, "247540": 178500, "035720": 61300}
    return {"stock_code": stock_code, "price": fake.get(stock_code, 0),
            "as_of": datetime.now().strftime("%H:%M")}
