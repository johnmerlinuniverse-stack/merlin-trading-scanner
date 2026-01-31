import os
import time
import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timezone
import joblib
from pathlib import Path

# Optional: ccxt
try:
    import ccxt
except Exception:
    ccxt = None

# ═══════════════════════════════════════════════════════════════════════
# 🎯 STRATEGY CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════

STRATEGY_CONFIG = {
    "Scalping (1m-15m)": {
        "pattern_tf_options": ["1m", "5m", "15m"],
        "signal_tf_options": ["1m", "5m"],
        "default_pattern_tf": "5m",
        "default_signal_tf": "1m",
        "min_confluence": 3,
        "tp_multiplier": 1.2,
        "sl_multiplier": 0.8,
        "ml_model_path": "ml/models/scalping_rf.pkl",
        "min_ml_score": 65,
        "lookback_bars": 100,
        "description": "Fast trades, 1-5min holds, tight stops"
    },
    "Intraday (15m-4H)": {
        "pattern_tf_options": ["15m", "30m", "1h", "4h"],
        "signal_tf_options": ["15m", "30m", "1h"],
        "default_pattern_tf": "1h",
        "default_signal_tf": "15m",
        "min_confluence": 4,
        "tp_multiplier": 2.0,
        "sl_multiplier": 1.0,
        "ml_model_path": "ml/models/intraday_rf.pkl",
        "min_ml_score": 70,
        "lookback_bars": 200,
        "description": "Medium trades, 1-8h holds, balanced risk"
    },
    "Swing (4H-1W)": {
        "pattern_tf_options": ["4h", "1d", "1w"],
        "signal_tf_options": ["4h", "1d"],
        "default_pattern_tf": "1d",
        "default_signal_tf": "4h",
        "min_confluence": 5,
        "tp_multiplier": 3.5,
        "sl_multiplier": 1.5,
        "ml_model_path": "ml/models/swing_rf.pkl",
        "min_ml_score": 75,
        "lookback_bars": 300,
        "description": "Position trades, days-weeks holds, wider stops"
    }
}

# ═══════════════════════════════════════════════════════════════════════
# 🎨 THEME & STYLING
# ═══════════════════════════════════════════════════════════════════════

def inject_theme_css(mode: str):
    if mode == "dark":
        bg = "#0B0F17"
        card = "#111827"
        card2 = "#0F172A"
        text = "#E5E7EB"
        muted = "#9CA3AF"
        border = "rgba(255,255,255,0.08)"
        accent = "#60A5FA"
        tablebg = "#0F172A"
        inputbg = "#0B1220"
    else:
        bg = "#F6F7FB"
        card = "#FFFFFF"
        card2 = "#FFFFFF"
        text = "#111827"
        muted = "#6B7280"
        border = "rgba(17,24,39,0.10)"
        accent = "#2563EB"
        tablebg = "#FFFFFF"
        inputbg = "#FFFFFF"

    st.markdown(f"""
<style>
:root {{
  --bg: {bg};
  --card: {card};
  --card2: {card2};
  --text: {text};
  --muted: {muted};
  --border: {border};
  --accent: {accent};
  --tablebg: {tablebg};
  --inputbg: {inputbg};
}}
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--bg) !important;
  color: var(--text) !important;
}}
.block-container {{
  padding-top: 2.4rem;
  padding-bottom: 1.2rem;
  max-width: 1200px;
}}
.strategy-card {{
  background: linear-gradient(135deg, var(--card), var(--card2));
  border: 2px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  margin: 10px 0;
  box-shadow: 0 10px 30px rgba(0,0,0,0.15);
}}
.ml-score-badge {{
  display: inline-block;
  padding: 8px 16px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 14px;
  margin: 4px;
}}
.score-high {{ background: linear-gradient(135deg, #00ff00, #00cc00); color: #000; }}
.score-medium {{ background: linear-gradient(135deg, #ffd700, #ffaa00); color: #000; }}
.score-low {{ background: linear-gradient(135deg, #ff6b6b, #cc0000); color: #fff; }}
.confluence-indicator {{
  display: inline-flex;
  gap: 4px;
  align-items: center;
}}
.confluence-dot {{
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}}
.dot-active {{ background: #00ff00; box-shadow: 0 0 8px #00ff00; }}
.dot-inactive {{ background: #333; }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 🔧 HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

CG_BASE = "https://api.coingecko.com/api/v3"
_CG_LAST_CALL = 0.0

TF_CCXT = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1d", "1w": "1w"
}

def timeframe_to_ms(tf: str) -> int:
    tf = tf.lower()
    if tf.endswith("m"):
        return int(tf[:-1]) * 60_000
    if tf.endswith("h"):
        return int(tf[:-1]) * 60 * 60_000
    if tf.endswith("d"):
        return int(tf[:-1]) * 24 * 60 * 60_000
    if tf.endswith("w"):
        return int(tf[:-1]) * 7 * 24 * 60 * 60_000
    return 0

# ═══════════════════════════════════════════════════════════════════════
# 🤖 ML INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_ml_model(model_path: str):
    """Load trained ML model with caching - OPTIONAL for Streamlit Cloud"""
    try:
        model_file = Path(model_path)
        if model_file.exists():
            return joblib.load(model_path)
        else:
            # No warning - ML is optional
            return None
    except Exception as e:
        # Silent fail - ML is optional
        return None

def calculate_confluence_score(setup_data: dict) -> tuple:
    """
    Calculate confluence score and return (score, reasons)
    """
    score = 0
    reasons = []
    
    # 1. Pattern Quality
    nr_type = setup_data.get('nr_type', '')
    if nr_type == 'NR10':
        score += 2
        reasons.append("🟣 NR10 Pattern")
    elif nr_type == 'NR7':
        score += 1
        reasons.append("🟡 NR7 Pattern")
    elif nr_type == 'NR4':
        score += 1
        reasons.append("🟢 NR4 Pattern")
    
    # 2. RSI Positioning
    rsi = setup_data.get('rsi_current', 50)
    if 40 <= rsi <= 60:
        score += 1
        reasons.append("📊 RSI Neutral")
    
    # 3. Volume
    if setup_data.get('volume_spike', False):
        score += 1
        reasons.append("📈 Volume Spike")
    
    # 4. Price Position
    if setup_data.get('price_state') == 'Inside':
        score += 1
        reasons.append("🎯 Inside Range")
    
    # 5. Range Active
    if setup_data.get('range_active', False):
        score += 1
        reasons.append("✅ Range Active")
    
    return score, reasons

def extract_ml_features(setup_data: dict, strategy_mode: str) -> dict:
    """
    Extract features for ML prediction based on strategy
    """
    base_features = {
        'nr_type_encoded': {'NR4': 1, 'NR7': 2, 'NR10': 3}.get(setup_data.get('nr_type', 'NR4'), 1),
        'rsi_current': setup_data.get('rsi_current', 50),
        'volume_spike': int(setup_data.get('volume_spike', False)),
        'price_state_encoded': {'Below': 0, 'Inside': 1, 'Above': 2}.get(setup_data.get('price_state', 'Inside'), 1),
        'range_active': int(setup_data.get('range_active', False)),
        'confluence_score': setup_data.get('confluence_score', 0),
        'setup_age_bars': setup_data.get('setup_age_bars', 0),
        'breakout_events': setup_data.get('breakout_events', 0),
    }
    
    if strategy_mode == "Scalping (1m-15m)":
        # Scalping-specific features
        base_features.update({
            'bars_since_breakout': setup_data.get('bars_since_breakout', 999),
            'hour_of_day': datetime.now().hour,
        })
    
    elif strategy_mode == "Intraday (15m-4H)":
        # Intraday-specific features
        base_features.update({
            'breakout_state_encoded': {'UP': 1, 'DOWN': -1, '-': 0}.get(setup_data.get('breakout_state', '-'), 0),
        })
    
    elif strategy_mode == "Swing (4H-1W)":
        # Swing-specific features
        base_features.update({
            'day_of_week': datetime.now().weekday(),
        })
    
    return base_features

def calculate_ml_score(features: dict, model, config: dict) -> dict:
    """
    Calculate ML score and predictions
    Falls back to confluence-based scoring if no model available
    """
    if model is None:
        # FALLBACK: Use Confluence-Based Scoring (works without ML!)
        confluence = features.get('confluence_score', 0)
        rsi = features.get('rsi_current', 50)
        nr_type = features.get('nr_type_encoded', 1)
        volume_spike = features.get('volume_spike', 0)
        
        # Calculate score from confluence + indicators
        base_score = (confluence / 5.0) * 60  # 0-60 from confluence
        
        # Bonus points
        if 40 <= rsi <= 60:  # RSI neutral
            base_score += 15
        if nr_type == 3:  # NR10
            base_score += 15
        elif nr_type == 2:  # NR7
            base_score += 10
        if volume_spike:
            base_score += 10
        
        ml_score = min(int(base_score), 100)
        win_prob = ml_score / 100.0
        
        if ml_score >= 75:
            confidence = "✅ High (No ML)"
        elif ml_score >= 60:
            confidence = "📊 Medium (No ML)"
        else:
            confidence = "⚠️ Low (No ML)"
        
        return {
            'ml_score': ml_score,
            'win_probability': win_prob,
            'confidence': confidence,
            'predicted_tp': None,
            'predicted_sl': None
        }
    
    # Original ML prediction code (if model exists)
    try:
        # Convert features to DataFrame (model expects this format)
        features_df = pd.DataFrame([features])
        
        # Get prediction probability
        win_prob = model.predict_proba(features_df)[0][1]
        ml_score = int(win_prob * 100)
        
        # Confidence level
        if win_prob >= 0.8:
            confidence = "🔥 High"
        elif win_prob >= 0.65:
            confidence = "✅ Medium"
        else:
            confidence = "⚠️ Low"
        
        # Predicted TP/SL (example calculation)
        entry_price = features.get('entry_price', 0)
        atr = features.get('atr', 0)
        
        if entry_price > 0 and atr > 0:
            predicted_tp = entry_price + (atr * config['tp_multiplier'])
            predicted_sl = entry_price - (atr * config['sl_multiplier'])
        else:
            predicted_tp = None
            predicted_sl = None
        
        return {
            'ml_score': ml_score,
            'win_probability': win_prob,
            'confidence': confidence,
            'predicted_tp': predicted_tp,
            'predicted_sl': predicted_sl
        }
    
    except Exception as e:
        st.error(f"ML prediction error: {e}")
        return {
            'ml_score': 0,
            'win_probability': 0,
            'confidence': 'Error',
            'predicted_tp': None,
            'predicted_sl': None
        }

# ═══════════════════════════════════════════════════════════════════════
# 🔍 CCXT FUNCTIONS (from your original code)
# ═══════════════════════════════════════════════════════════════════════

PROVIDER_CHAIN = ["bitget", "bingx", "bybit", "mexc", "blofin", "okx"]

@st.cache_resource(ttl=3600)
def get_exchange_client(exchange_id: str):
    if ccxt is None:
        raise RuntimeError("ccxt not installed")
    if not hasattr(ccxt, exchange_id):
        raise RuntimeError(f"ccxt doesn't support {exchange_id}")
    klass = getattr(ccxt, exchange_id)
    ex = klass({"enableRateLimit": True, "timeout": 20000})
    ex.options = {**ex.options, "defaultType": "swap"}
    return ex

@st.cache_data(ttl=3600)
def load_markets_cached(exchange_id: str):
    ex = get_exchange_client(exchange_id)
    return ex.load_markets()

def find_ccxt_futures_symbol(exchange_id: str, base_sym: str):
    markets = load_markets_cached(exchange_id)
    candidates = []
    for sym, m in markets.items():
        if (m.get("base") or "").upper() != base_sym.upper():
            continue
        quote = m.get("quote") or ""
        if quote != "USDT":
            continue
        if not m.get("active", True):
            continue
        candidates.append((sym, m))
    
    if not candidates:
        return None
    
    def score(sym, m):
        s = 0
        if ":USDT" in sym:
            s += 3
        if m.get("swap"):
            s += 2
        if m.get("linear"):
            s += 1
        return s
    
    candidates.sort(key=lambda x: score(x[0], x[1]), reverse=True)
    return candidates[0][0]

def fetch_ohlcv_ccxt(exchange_id: str, ccxt_symbol: str, timeframe: str, limit: int = 300):
    ex = get_exchange_client(exchange_id)
    ohlcv = ex.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)
    if not ohlcv or len(ohlcv) < 15:
        return None
    
    ohlcv = ohlcv[:-1]  # Remove in-progress candle
    if len(ohlcv) < 12:
        return None
    
    rows = []
    for ts, o, h, l, c, v in ohlcv:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
        rows.append({
            "ts_ms": int(ts),
            "time": dt,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": float(v),
            "range": float(h - l),
        })
    return rows

# ═══════════════════════════════════════════════════════════════════════
# 📊 NR PATTERN DETECTION (from your original code)
# ═══════════════════════════════════════════════════════════════════════

def compute_nr_flags(closed):
    n = len(closed)
    rngs = [c["range"] for c in closed]
    nr10 = [False] * n
    nr7 = [False] * n
    nr4 = [False] * n
    
    for i in range(n):
        w10 = rngs[max(0, i - 9): i + 1]
        w7 = rngs[max(0, i - 6): i + 1]
        w4 = rngs[max(0, i - 3): i + 1]
        
        lst10 = min(w10) if len(w10) >= 10 else None
        lst7 = min(w7) if len(w7) >= 7 else None
        lst4 = min(w4) if len(w4) >= 4 else None
        
        is10 = (lst10 is not None and rngs[i] == lst10)
        is7 = (lst7 is not None and rngs[i] == lst7 and (not is10))
        is4 = (lst4 is not None and rngs[i] == lst4 and (not is7) and (not is10))
        
        nr10[i] = is10
        nr7[i] = is7
        nr4[i] = is4
    
    return nr4, nr7, nr10

def find_last_nr_setup(pattern_bars):
    if len(pattern_bars) < 12:
        return None
    
    nr4_flags, nr7_flags, nr10_flags = compute_nr_flags(pattern_bars)
    
    setup_idx = -1
    setup_type = ""
    for i in range(len(pattern_bars) - 1, -1, -1):
        if nr10_flags[i] or nr7_flags[i] or nr4_flags[i]:
            setup_idx = i
            setup_type = "NR10" if nr10_flags[i] else ("NR7" if nr7_flags[i] else "NR4")
            break
    
    if setup_idx == -1:
        return None
    
    bar = pattern_bars[setup_idx]
    rh = float(bar["high"])
    rl = float(bar["low"])
    mid = (rh + rl) / 2.0
    setup_ts = int(bar["ts_ms"])
    setup_time = str(bar["time"])
    
    return {
        "setup_idx": setup_idx,
        "setup_type": setup_type,
        "rh": rh,
        "rl": rl,
        "mid": mid,
        "setup_ts": setup_ts,
        "setup_time": setup_time,
        "nr4": bool(nr4_flags[setup_idx]),
        "nr7": bool(nr7_flags[setup_idx]),
        "nr10": bool(nr10_flags[setup_idx]),
    }

def simulate_breakouts_on_signal(signal_bars, rh, rl):
    if not signal_bars or len(signal_bars) < 3:
        return {
            "breakout_state": "-",
            "breakout_tag": "-",
            "event_count": 0,
            "last_break_idx": None,
        }
    
    mid = (rh + rl) / 2.0
    up_check = True
    down_check = True
    event_count = 0
    breakout_state = "-"
    breakout_tag = "-"
    last_break_idx = None
    
    for j in range(1, len(signal_bars)):
        prev_close = float(signal_bars[j - 1]["close"])
        cur_close = float(signal_bars[j]["close"])
        
        if cur_close > mid and down_check is False:
            down_check = True
        
        if (prev_close >= rl) and (cur_close < rl) and down_check:
            event_count += 1
            down_check = False
            breakout_state = "DOWN"
            breakout_tag = f"DOWN#{event_count}"
            last_break_idx = j
        
        if cur_close < mid and up_check is False:
            up_check = True
        
        if (prev_close <= rh) and (cur_close > rh) and up_check:
            event_count += 1
            up_check = False
            breakout_state = "UP"
            breakout_tag = f"UP#{event_count}"
            last_break_idx = j
    
    return {
        "breakout_state": breakout_state,
        "breakout_tag": breakout_tag,
        "event_count": event_count,
        "last_break_idx": last_break_idx,
    }

def compute_range_active(signal_bars, setup_ts, pattern_tf_ms, rh, rl):
    if not signal_bars:
        return False, 0, False, 0
    
    setup_close_ts = setup_ts + pattern_tf_ms
    setup_age_bars = len(signal_bars)
    
    def block_index(ts_ms: int) -> int:
        if ts_ms < setup_close_ts:
            return -1
        return int((ts_ms - setup_close_ts) // pattern_tf_ms)
    
    current_block = block_index(int(signal_bars[-1]["ts_ms"]))
    if current_block < 0:
        current_block = 0
    
    block_break = {}
    for j in range(1, len(signal_bars)):
        prev_close = float(signal_bars[j - 1]["close"])
        cur_close = float(signal_bars[j]["close"])
        ts = int(signal_bars[j]["ts_ms"])
        b = block_index(ts)
        if b < 0:
            continue
        
        broke = False
        if (prev_close >= rl) and (cur_close < rl):
            broke = True
        if (prev_close <= rh) and (cur_close > rh):
            broke = True
        
        if broke:
            block_break[b] = True
    
    last_block_has_breakout = bool(block_break.get(current_block, False))
    nr_active_now = (current_block == 0)
    range_active_now = bool(nr_active_now or last_block_has_breakout)
    
    return range_active_now, setup_age_bars, last_block_has_breakout, current_block

# ═══════════════════════════════════════════════════════════════════════
# 🎨 UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════

def render_ml_score_badge(ml_score: int):
    """Render ML score as colored badge"""
    if ml_score >= 75:
        badge_class = "score-high"
        emoji = "🔥"
    elif ml_score >= 60:
        badge_class = "score-medium"
        emoji = "✅"
    else:
        badge_class = "score-low"
        emoji = "⚠️"
    
    return f'<span class="ml-score-badge {badge_class}">{emoji} {ml_score}%</span>'

def render_confluence_dots(score: int, max_score: int = 5):
    """Render confluence as dots"""
    dots_html = '<div class="confluence-indicator">'
    for i in range(max_score):
        dot_class = "dot-active" if i < score else "dot-inactive"
        dots_html += f'<span class="confluence-dot {dot_class}"></span>'
    dots_html += '</div>'
    return dots_html

# ═══════════════════════════════════════════════════════════════════════
# 🚀 MAIN APP
# ═══════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="🧙‍♂️ Merlin's ML Trading Scanner",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Session state
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "dark"
    
    # Apply theme
    inject_theme_css(st.session_state["theme_mode"])
    
    # ═══════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown("""
        <div class="strategy-card">
            <h1 style='margin:0'>🧙‍♂️ MERLIN'S ML TRADING SCANNER</h1>
            <p style='margin:0; color: var(--muted); font-size: 14px;'>
                AI-Powered Multi-Strategy Crypto Scanner with Machine Learning
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        theme_label = "🌙 Dark" if st.session_state["theme_mode"] == "dark" else "☀️ Light"
        if st.button(f"{theme_label}", use_container_width=True):
            st.session_state["theme_mode"] = "light" if st.session_state["theme_mode"] == "dark" else "dark"
            st.rerun()
    
    # ═══════════════════════════════════════════════════════════════════
    # SIDEBAR: STRATEGY SELECTION
    # ═══════════════════════════════════════════════════════════════════
    
    with st.sidebar:
        st.markdown("## 🎯 Strategy Selection")
        
        strategy_mode = st.selectbox(
            "Trading Strategy",
            list(STRATEGY_CONFIG.keys()),
            index=1,  # Default: Intraday
            help="Select your trading timeframe"
        )
        
        config = STRATEGY_CONFIG[strategy_mode]
        
        st.info(f"**{strategy_mode}**\n\n{config['description']}")
        
        st.markdown("---")
        st.markdown("## ⚙️ Settings")
        
        # Timeframe Selection
        pattern_tf = st.selectbox(
            "Pattern Timeframe",
            config["pattern_tf_options"],
            index=config["pattern_tf_options"].index(config["default_pattern_tf"])
        )
        
        signal_tf = st.selectbox(
            "Signal Timeframe",
            config["signal_tf_options"],
            index=config["signal_tf_options"].index(config["default_signal_tf"])
        )
        
        st.markdown("---")
        st.markdown("## 🤖 ML Settings")
        
        min_ml_score = st.slider(
            "Min ML Score",
            min_value=50,
            max_value=95,
            value=config["min_ml_score"],
            step=5,
            help="Only show setups with ML score above this threshold"
        )
        
        min_confluence = st.slider(
            "Min Confluence",
            min_value=1,
            max_value=5,
            value=config["min_confluence"],
            help="Minimum number of confluence factors required"
        )
        
        st.markdown("---")
        st.markdown("## 🎛️ Filters")
        
        show_only_inside = st.checkbox(
            "Only Inside Range",
            value=False,
            help="Show only coins currently inside NR range"
        )
        
        show_only_active = st.checkbox(
            "Only Active Ranges",
            value=False,
            help="Show only setups with active ranges (LuxAlgo style)"
        )
        
        st.markdown("---")
        
        # Coin Selection
        st.markdown("## 💰 Coin Selection")
        coin_input = st.text_area(
            "Coins to Scan (one per line)",
            value="BTC\nETH\nBNB\nSOL\nADA\nDOGE\nXRP\nAVAX\nLINK\nDOT",
            height=150
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # MAIN CONTENT
    # ═══════════════════════════════════════════════════════════════════
    
    # Load ML Model (optional - works without it!)
    model = load_ml_model(config["ml_model_path"])
    
    # Scan Button
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        scan_button = st.button("🚀 Start Scan", type="primary", use_container_width=True)
    with col2:
        st.metric("Strategy", strategy_mode.split()[0])
    with col3:
        mode_label = "✅ ML Mode" if model else "📊 Confluence"
        mode_color = "normal" if model else "inverse"
        st.metric("Scoring", mode_label)
    
    if not scan_button:
        st.info("👆 Click 'Start Scan' to begin searching for trading opportunities")
        return
    
    # ═══════════════════════════════════════════════════════════════════
    # SCANNING LOGIC
    # ═══════════════════════════════════════════════════════════════════
    
    # Parse coins
    coins = [line.strip().upper() for line in coin_input.split('\n') if line.strip()]
    
    if not coins:
        st.error("Please enter at least one coin symbol")
        return
    
    st.markdown(f"### 🔍 Scanning {len(coins)} coins...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    skipped = []
    errors = []
    
    ccxt_pattern_tf = TF_CCXT.get(pattern_tf, "1h")
    ccxt_signal_tf = TF_CCXT.get(signal_tf, "15m")
    pattern_tf_ms = timeframe_to_ms(ccxt_pattern_tf)
    
    # Scan each coin
    for i, coin in enumerate(coins):
        progress = (i + 1) / len(coins)
        progress_bar.progress(progress)
        status_text.text(f"Scanning {coin}... ({i+1}/{len(coins)})")
        
        pattern_bars = None
        signal_bars = None
        exchange_used = ""
        pair_used = ""
        
        # Try exchanges in chain
        for ex_id in PROVIDER_CHAIN:
            try:
                if not hasattr(ccxt, ex_id):
                    continue
                
                # Find symbol
                sym = find_ccxt_futures_symbol(ex_id, coin)
                if not sym:
                    continue
                
                # Fetch pattern data
                pb = fetch_ohlcv_ccxt(ex_id, sym, timeframe=ccxt_pattern_tf, limit=config["lookback_bars"])
                if not pb:
                    continue
                
                # Find NR setup
                setup = find_last_nr_setup(pb)
                if setup is None:
                    continue
                
                # Fetch signal data
                start_after_close = setup["setup_ts"] + pattern_tf_ms
                sb = fetch_ohlcv_ccxt(ex_id, sym, timeframe=ccxt_signal_tf, limit=350, since_ms=start_after_close)
                if not sb:
                    continue
                
                pattern_bars = pb
                signal_bars = sb
                exchange_used = ex_id
                pair_used = sym
                break
                
            except Exception as e:
                continue
        
        if pattern_bars is None or signal_bars is None:
            skipped.append(f"{coin}: No data")
            continue
        
        try:
            # Analyze setup
            setup = find_last_nr_setup(pattern_bars)
            if setup is None:
                skipped.append(f"{coin}: No NR setup")
                continue
            
            rh = setup["rh"]
            rl = setup["rl"]
            
            # Breakouts
            binfo = simulate_breakouts_on_signal(signal_bars, rh=rh, rl=rl)
            
            # Current state
            last_close = float(signal_bars[-1]["close"])
            last_volume = float(signal_bars[-1]["volume"])
            
            # Calculate average volume
            avg_volume = np.mean([float(b["volume"]) for b in signal_bars[-20:]])
            volume_spike = last_volume > avg_volume * 1.5
            
            # Price state
            lo = min(rl, rh)
            hi = max(rl, rh)
            if last_close > hi:
                price_state = "Above"
            elif last_close < lo:
                price_state = "Below"
            else:
                price_state = "Inside"
            
            # Range active
            range_active, setup_age_bars, _, _ = compute_range_active(
                signal_bars, setup["setup_ts"], pattern_tf_ms, rh, rl
            )
            
            # Calculate RSI
            closes = [float(b["close"]) for b in signal_bars[-14:]]
            rsi_current = calculate_rsi(closes, 14)
            
            # Bars since breakout
            bars_since = "-"
            if isinstance(binfo["last_break_idx"], int):
                bars_since = (len(signal_bars) - 1) - binfo["last_break_idx"]
            
            # Calculate ATR
            atr = calculate_atr(signal_bars[-20:])
            
            # Prepare setup data for confluence
            setup_data = {
                'nr_type': setup["setup_type"],
                'rsi_current': rsi_current,
                'volume_spike': volume_spike,
                'price_state': price_state,
                'range_active': range_active,
                'setup_age_bars': setup_age_bars,
                'breakout_events': binfo["event_count"],
                'breakout_state': binfo["breakout_state"],
                'bars_since_breakout': bars_since if bars_since != "-" else 999,
                'entry_price': last_close,
                'atr': atr
            }
            
            # Calculate confluence
            confluence_score, confluence_reasons = calculate_confluence_score(setup_data)
            setup_data['confluence_score'] = confluence_score
            
            # Apply filters
            if show_only_inside and price_state != "Inside":
                continue
            
            if show_only_active and not range_active:
                continue
            
            if confluence_score < min_confluence:
                continue
            
            # Extract ML features
            ml_features = extract_ml_features(setup_data, strategy_mode)
            
            # ML Prediction
            ml_result = calculate_ml_score(ml_features, model, config)
            
            # Filter by ML score
            if ml_result['ml_score'] < min_ml_score:
                continue
            
            # Calculate TP/SL
            tp_price = last_close + (atr * config['tp_multiplier'])
            sl_price = last_close - (atr * config['sl_multiplier'])
            risk_reward = config['tp_multiplier'] / config['sl_multiplier']
            
            # Add to results
            results.append({
                'symbol': coin,
                'exchange': exchange_used,
                'pair': pair_used,
                'pattern': setup["setup_type"],
                'ml_score': ml_result['ml_score'],
                'win_probability': ml_result['win_probability'],
                'confidence': ml_result['confidence'],
                'confluence_score': confluence_score,
                'confluence_reasons': confluence_reasons,
                'price_state': price_state,
                'range_active': range_active,
                'breakout_state': binfo["breakout_state"],
                'breakout_tag': binfo["breakout_tag"],
                'last_close': last_close,
                'predicted_tp': tp_price,
                'predicted_sl': sl_price,
                'risk_reward': risk_reward,
                'rsi': rsi_current,
                'volume_spike': volume_spike,
                'setup_age': setup_age_bars,
                'setup_time': setup["setup_time"]
            })
            
        except Exception as e:
            errors.append(f"{coin}: {str(e)[:100]}")
    
    progress_bar.progress(1.0)
    status_text.text("✅ Scan complete!")
    
    # ═══════════════════════════════════════════════════════════════════
    # DISPLAY RESULTS
    # ═══════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    if not results:
        st.warning(f"No setups found matching criteria. Skipped: {len(skipped)}, Errors: {len(errors)}")
        
        with st.expander("📋 Scan Report"):
            st.write("**Skipped:**")
            for s in skipped[:50]:
                st.text(s)
            if errors:
                st.write("**Errors:**")
                for e in errors[:50]:
                    st.text(e)
        return
    
    # Sort by ML score
    results.sort(key=lambda x: x['ml_score'], reverse=True)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ Setups Found", len(results))
    col2.metric("⏭️ Skipped", len(skipped))
    col3.metric("⚠️ Errors", len(errors))
    col4.metric("🎯 Avg ML Score", f"{np.mean([r['ml_score'] for r in results]):.0f}%")
    
    st.markdown("### 🏆 TOP TRADING OPPORTUNITIES")
    
    # Display top results
    for i, setup in enumerate(results[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
        
        with st.expander(f"{medal} {setup['symbol']} - ML Score: {setup['ml_score']}% - {setup['confidence']}", expanded=(i<=3)):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"""
                **🎯 Setup Details**
                - Pattern: **{setup['pattern']}**
                - Exchange: {setup['exchange'].upper()}
                - Pair: `{setup['pair']}`
                - State: {setup['price_state']}
                - Range: {'✅ Active' if setup['range_active'] else '⏸️ Frozen'}
                """)
            
            with col2:
                st.markdown(f"""
                **📊 Indicators**
                - RSI: {setup['rsi']:.1f}
                - Volume: {'📈 Spike' if setup['volume_spike'] else '📊 Normal'}
                - Breakout: {setup['breakout_tag']}
                - Setup Age: {setup['setup_age']} bars
                """)
            
            with col3:
                st.markdown(f"""
                **🎯 Trade Plan**
                - Entry: ${setup['last_close']:.2f}
                - TP: ${setup['predicted_tp']:.2f}
                - SL: ${setup['predicted_sl']:.2f}
                - R:R: 1:{setup['risk_reward']:.1f}
                """)
            
            # Confluence
            st.markdown("**🔗 Confluence Factors:**")
            confluence_html = render_confluence_dots(setup['confluence_score'])
            st.markdown(confluence_html, unsafe_allow_html=True)
            for reason in setup['confluence_reasons']:
                st.markdown(f"- {reason}")
            
            # ML Score Badge
            ml_badge = render_ml_score_badge(setup['ml_score'])
            st.markdown(f"**ML Prediction:** {ml_badge} Win Probability: {setup['win_probability']:.1%}", unsafe_allow_html=True)
    
    # Full table
    st.markdown("### 📊 All Results")
    df_display = pd.DataFrame(results)
    df_display = df_display[[
        'symbol', 'ml_score', 'confluence_score', 'pattern', 
        'price_state', 'breakout_tag', 'last_close', 
        'predicted_tp', 'risk_reward'
    ]]
    df_display.columns = [
        'Coin', 'ML Score', 'Confluence', 'Pattern',
        'State', 'Breakout', 'Price', 'TP Target', 'R:R'
    ]
    st.dataframe(df_display, use_container_width=True)
    
    # CSV Export
    csv = pd.DataFrame(results).to_csv(index=False)
    st.download_button(
        "📥 Download Full Report (CSV)",
        csv,
        f"merlin_scan_{strategy_mode.split()[0]}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv",
        use_container_width=True
    )

# Helper functions for RSI and ATR
def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    if len(prices) < period + 1:
        return 50
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(bars, period=14):
    """Calculate ATR"""
    if len(bars) < period:
        return 0
    
    trs = []
    for i in range(1, len(bars)):
        h = bars[i]['high']
        l = bars[i]['low']
        c_prev = bars[i-1]['close']
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    
    return np.mean(trs[-period:])

if __name__ == "__main__":
    main()
