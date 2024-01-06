import json
import os
import redis
from typing import Union

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pybit.unified_trading import HTTP

db = redis.Redis(host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT"))

session = HTTP(
    testnet=False,
    api_key="...",
    api_secret="...",
)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/test_redis")
def test_redis():
    db.set("test", json.dumps({"hoi": "doei"}))
    output = db.get("test")
    return output


@app.get('/api/orderbook')
async def orderbook(symbol:str="BTCUSDT"):
    orderbook = session.get_orderbook(category="linear", symbol=symbol)
    return orderbook


@app.get("/api/symbols/")
def get_symbols():
    # TODO inplement database
    # types:
    #    inverse – Inverse Contracts;
    #    linear  – USDT Perpetual, USDC Contracts;
    #    spot    – Spot Trading;
    #    option  – USDC Options;
    symbols = []
    symbols.append({'symbol':'BTCUSDT', 'type':'linear'})
    symbols.append({'symbol':'ETHUSDT', 'type':'linear'})
    symbols.append({'symbol':'SOLUSDT', 'type':'linear'})
    symbols.append({'symbol':'OPUSDT', 'type':'linear'})
    symbols.append({'symbol':'ARBUSDT', 'type':'linear'})
    return symbols
