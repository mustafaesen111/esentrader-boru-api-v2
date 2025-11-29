from uuid import uuid4
from datetime import datetime
from . import copy_engine


def now_iso():
    return datetime.utcnow().isoformat()


def place_master_trade(broker, symbol, side, usd_amount, meta=None):
    if meta is None:
        meta = {}

    side = side.upper()  # BUY / SELL

    price = broker.get_price(symbol)
    if not price or price <= 0:
        raise RuntimeError(f"Price not found: {symbol}, price={price}")

    qty = usd_amount / price

    if hasattr(broker, "adjust_quantity"):
        qty = broker.adjust_quantity(symbol, qty)

    if qty <= 0:
        raise RuntimeError(f"Calculated qty <= 0: {qty}")

    order_id = broker.place_order(
        symbol=symbol,
        side=side,
        quantity=qty,
        order_type="MKT"
    )

    master_event = {
        "event_type": "MASTER_TRADE",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "usd_amount": usd_amount,
        "source": meta.get("source"),
        "strategy": meta.get("strategy"),
        "signal_id": meta.get("signal_id"),
        "ts": now_iso(),
        "order_id": order_id,
        "master_trade_id": uuid4().hex,
    }

    copy_engine.enqueue(master_event)

    return master_event
