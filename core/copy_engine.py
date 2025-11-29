def enqueue(event: dict):
    print(f"[COPY_ENGINE] enqueue event: {event}")
    process_master_trade(event)


def process_master_trade(event: dict):
    symbol = event.get("symbol")
    side = event.get("side")
    qty = event.get("qty")
    usd = event.get("usd_amount")

    print(f"[COPY_ENGINE] (FAKE) would copy to followers: "
          f"{symbol} {side} qty={qty} usd={usd}")

    # TODO: Followers table, equity scaling, broker dispatch
