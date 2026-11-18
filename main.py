import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

LOOK = 30
BUY_RETURN_BPS = -120
BUY_Z = -1.0
MIN_CASH = 1_000_000
SLIPPAGE = 300
SELL_UP_BPS = 80
SELL_DOWN_BPS = -200
# Hold up to 75 bars to allow longer recovery time after a drawdown before forced exit.
HOLD_BARS = 75

_closes = {}
_symbol = None
_entry_ref = None
_entry_seq = None
_pending_buy = False


def _update_closes(batch):
    for bar in batch.get("bars", []):
        _closes.setdefault(bar["symbol"], []).append(int(bar["c"]))


def on_batch(state, batch):
    global _symbol, _entry_ref, _entry_seq, _pending_buy

    _update_closes(batch)

    if state.warming_up:
        return []

    if _symbol is None:
        _symbol = next(iter(state.symbols))

    orders = []

    if _symbol in state.positions:
        _pending_buy = False
        held = state.positions[_symbol]
        price = state.close(_symbol)
        bars_held = state.seq - _entry_seq
        if (
            price >= int(_entry_ref * (1 + SELL_UP_BPS / 10_000))
            or price <= int(_entry_ref * (1 + SELL_DOWN_BPS / 10_000))
            or bars_held >= HOLD_BARS
        ):
            orders.append(
                {"side": "sell", "symbol": _symbol, "qty": held.qty, "max_slippage_bps": SLIPPAGE}
            )
            _entry_ref = None
            _entry_seq = None
    elif not _pending_buy and state.cash >= MIN_CASH:
        hist = _closes.get(_symbol, [])
        if len(hist) >= LOOK:
            window = hist[-LOOK:]
            c_now = window[-1]
            c_old = window[0]
            ret_bps = (c_now - c_old) * 10_000 // c_old if c_old else 0
            mean = sum(window) / len(window)
            var = sum((x - mean) ** 2 for x in window) / len(window)
            std = var ** 0.5
            z = (c_now - mean) / std if std > 0 else 0.0
            if ret_bps < BUY_RETURN_BPS and z < BUY_Z:
                orders.append(
                    {
                        "side": "buy",
                        "symbol": _symbol,
                        "notional_quote_units": int(state.cash),
                        "max_slippage_bps": SLIPPAGE,
                    }
                )
                _entry_ref = state.close(_symbol)
                _entry_seq = state.seq
                _pending_buy = True

    return orders


makefun_bars.run(on_batch)