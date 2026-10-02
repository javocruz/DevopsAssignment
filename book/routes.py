from fastapi import APIRouter, Depends

from book.repo import list_bets, total_pnl
from db import get_db

router = APIRouter()


@router.get("/portfolio")
def get_portfolio(conn=Depends(get_db)):
    return {"bets": list_bets(conn), "total_pnl": total_pnl(conn)}
