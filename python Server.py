import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("Binance Futures Market Data")

BASE_URL = "https://fapi.binance.com"
TIMEOUT = 20


def binance_get(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool
def list_usdt_perpetuals() -> list[str]:
    """List active Binance USD-M USDT perpetual symbols."""
    data = binance_get("/fapi/v1/exchangeInfo")

    return sorted(
        item["symbol"]
        for item in data["symbols"]
        if item.get("status") == "TRADING"
        and item.get("contractType") == "PERPETUAL"
        and item.get("quoteAsset") == "USDT"
    )


@mcp.tool
def get_futures_price(symbol: str) -> dict:
    """Get current price and 24-hour statistics for a symbol."""
    symbol = symbol.strip().upper()

    price = binance_get(
        "/fapi/v1/ticker/price",
        {"symbol": symbol},
    )
    stats = binance_get(
        "/fapi/v1/ticker/24hr",
        {"symbol": symbol},
    )

    return {
        "symbol": symbol,
        "price": price["price"],
        "price_change_percent_24h": stats["priceChangePercent"],
        "high_24h": stats["highPrice"],
        "low_24h": stats["lowPrice"],
        "volume_24h": stats["volume"],
        "quote_volume_24h": stats["quoteVolume"],
    }


@mcp.tool
def get_futures_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 500,
) -> list[dict]:
    """Get Binance futures OHLCV candles, oldest first."""
    symbol = symbol.strip().upper()
    allowed_intervals = {
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "6h", "8h", "12h",
        "1d", "3d", "1w", "1M",
    }

    if interval not in allowed_intervals:
        raise ValueError("Unsupported candle interval.")

    if not 1 <= limit <= 1500:
        raise ValueError("limit must be between 1 and 1500.")

    rows = binance_get(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    return [
        {
            "open_time": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
            "close_time": row[6],
            "quote_volume": row[7],
            "trade_count": row[8],
            "taker_buy_base_volume": row[9],
            "taker_buy_quote_volume": row[10],
        }
        for row in rows
    ]


@mcp.tool
def get_futures_order_book(
    symbol: str,
    limit: int = 20,
) -> dict:
    """Get current futures order-book bids and asks."""
    symbol = symbol.strip().upper()

    if limit not in {5, 10, 20, 50, 100, 500, 1000}:
        raise ValueError("Unsupported order-book limit.")

    return binance_get(
        "/fapi/v1/depth",
        {"symbol": symbol, "limit": limit},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
    )
