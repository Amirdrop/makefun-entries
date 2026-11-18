import os
import sys
import statistics

# Add sibling 'vendor' directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vendor'))

import makefun_bars

closes = []
entry_close = None
held = 0

def on_batch(state, batch):
    global closes, entry_close, held

    # state.symbols is a dict mapping symbol->spec, not a list
    sym = 'CBBTC' if 'CBBTC' in state.symbols else next(iter(state.symbols))
    bar = state.latest.get(sym)
    if bar is None:
        return []
    close = float(bar['c'])
    closes.append(close)

    orders = []
    pos = state.positions.get(sym)

    if pos and pos.qty > 0:
        held += 1
        g = (close / entry_close - 1) * 10000
        if g >= 80 or g <= -200 or held >= 60:
            orders.append({
                'side': 'sell',
                'symbol': sym,
                'qty': pos.qty,
                'max_slippage_bps': 300
            })
            entry_close = None
            held = 0
    else:
        if not state.warming_up and len(closes) > 31:
            w = closes[-31:]
            ret = (closes[-1] / w[0] - 1) * 10000
            mu = statistics.mean(w)
            sd = statistics.pstdev(w)
            z = (closes[-1] - mu) / (sd or 1.0)
            if ret < -120 and z < -1.0 and state.cash >= 1000000:
                orders.append({
                    'side': 'buy',
                    'symbol': sym,
                    'notional_quote_units': int(state.cash),
                    'max_slippage_bps': 300
                })
                entry_close = close
                held = 0

    return orders

makefun_bars.run(on_batch)
