# 🧙‍♂️ MERLIN'S ML TRADING SYSTEM - COMPLETE SETUP GUIDE

## 📦 SYSTEM OVERVIEW

This is a complete 2-stage trading system:
1. **Scanner (Web App)**: ML-powered scanner finds best setups across markets
2. **TradingView Indicator**: Visual confirmation with Simple Mode for clean signals

### **3 Trading Strategies Supported:**
- **Scalping** (1m-15m): Fast trades, 1-5min holds
- **Intraday** (15m-4H): Medium trades, 1-8h holds
- **Swing** (4H-1W): Position trades, days-weeks holds

---

## 🚀 QUICK START (5 MINUTES)

### **Step 1: Install Python Dependencies**

```bash
# Install requirements
pip install -r requirements.txt

# Verify ccxt is installed
python -c "import ccxt; print('CCXT Version:', ccxt.__version__)"
```

### **Step 2: Run Scanner WITHOUT ML (Fast Start)**

```bash
# Run scanner directly (works without ML models)
streamlit run merlin_scanner_ml.py
```

The scanner will work but show "⚠️ ML Model not loaded" warnings.

### **Step 3: Add TradingView Indicator**

1. Open TradingView
2. Pine Editor → New Indicator
3. Copy content from `merlin_matrix_v6_ml.pine`
4. Click "Add to Chart"
5. Enable **🎯 Simple Mode** in settings
6. Select your **Trading Strategy**

**Done!** You now have a working system.

---

## 🤖 FULL ML SETUP (WITH TRAINED MODELS)

For ML-powered predictions, follow these steps:

### **Phase 1: Collect Training Data (15-30 min)**

```bash
# Collect data for all strategies
python ml/collect_training_data.py --strategy all

# Or collect for specific strategy
python ml/collect_training_data.py --strategy intraday
```

**What this does:**
- Fetches 30-180 days of historical data (depending on strategy)
- Finds all NR4/NR7/NR10 patterns
- Calculates if each setup was profitable
- Saves to `ml/data/training_data_*.csv`

**Expected Output:**
```
COLLECTION SUMMARY
Total Setups: 450
Win Rate: 62.3%
Avg Profit (Winners): 3.45%
Avg Loss (Losers): -1.82%
```

### **Phase 2: Train ML Models (5-10 min)**

```bash
# Train all models
python ml/train_models.py --strategy all

# Or train specific strategy
python ml/train_models.py --strategy intraday
```

**What this does:**
- Trains Random Forest models on collected data
- Validates with 5-fold cross-validation
- Shows feature importance
- Saves models to `ml/models/*.pkl`

**Expected Output:**
```
MODEL EVALUATION
Accuracy: 0.673
             precision    recall  f1-score
Loss            0.65      0.72      0.68
Win             0.70      0.63      0.66
```

### **Phase 3: Test Models (2-3 min)**

```bash
# Test on recent market data
python ml/test_models.py --strategy intraday
```

**What this does:**
- Tests model on last 7 days of real data
- Shows predictions for major coins
- Saves results to `ml/test_results_*.csv`

---

## 📊 USING THE SCANNER

### **Basic Workflow:**

1. **Open Scanner**
   ```bash
   streamlit run merlin_scanner_ml.py
   ```

2. **Select Strategy**
   - Sidebar → "Trading Strategy"
   - Choose: Scalping / Intraday / Swing

3. **Configure Filters**
   - Min ML Score: 70% (higher = more selective)
   - Min Confluence: 4/5 (default for Intraday)
   - Optional: "Only Inside Range", "Only Active Ranges"

4. **Enter Coins**
   - Add coin symbols (one per line)
   - Default list includes BTC, ETH, BNB, etc.

5. **Scan**
   - Click "🚀 Start Scan"
   - Wait for results (~30 sec for 10 coins)

6. **Review Results**
   - Top 10 setups ranked by ML Score
   - Confluence factors shown
   - Predicted TP/SL levels

### **Understanding the Output:**

```
🥇 BTC - ML Score: 94%
  Pattern: NR7 (1H)
  Confluence: 5/5
    🟡 NR7 Pattern
    ✅ ST Buy
    📊 RSI Neutral
    📈 EMA Bull
    📈 Volume Spike
  ML Prediction: 🔥 High | Win Prob: 94%
  Trade Plan:
    Entry: $67,234.50
    TP: $68,890.00
    SL: $66,100.00
    R:R: 1:2.0
```

**What this means:**
- **ML Score 94%**: Model predicts 94% chance this trade wins
- **Confluence 5/5**: All 5 factors align
- **Win Prob 94%**: Same as ML score (probability format)
- **R:R 1:2.0**: Risk $1 to make $2

---

## 🎯 USING TRADINGVIEW INDICATOR

### **Setup:**

1. Add indicator to chart
2. Go to Settings (gear icon)
3. Configure:

**Display Mode:**
- ✅ Enable **🎯 Simple Mode** (clean view)
- ✅ Show Entry Price
- ✅ Show Take Profit
- ✅ Show Stop Loss
- ✅ Show Confluence Score

**Trading Strategy:**
- Select: Scalping / Intraday / Swing

**Toggle Indicators** (only visible in Full Mode):
- Enable NR4/NR7/NR10
- Enable SuperTrend V
- Enable EMAs
- (Disable others for cleaner chart)

### **Simple Mode View:**

When enabled, you'll see:
- **BUY/SELL arrows** (large, green/red)
- **Entry line** (yellow, horizontal)
- **TP line** (green, dashed)
- **SL line** (red, dotted)
- **Confluence label** (shows factors)

### **Full Mode View:**

Shows all indicators:
- NR patterns with ranges
- SuperTrend line
- EMAs
- Zone Shift
- All other enabled indicators

### **Alerts:**

Set up alerts for:
- 🟢 Master BUY Signal
- 🔴 Master SELL Signal
- 🎯 TP Hit (Long)
- 🎯 TP Hit (Short)

---

## 📋 COMPLETE TRADING WORKFLOW

### **1. Morning: Scanner Phase**

```bash
# Run scanner
streamlit run merlin_scanner_ml.py

# Settings:
- Strategy: Intraday
- Min ML Score: 75%
- Min Confluence: 4/5
```

**Output:** List of 5-10 high-probability setups

### **2. Confirmation: TradingView Phase**

For each coin from scanner:

1. Open coin chart in TradingView
2. Check Merlin indicator (Simple Mode ON)
3. Look for:
   - ✅ Buy/Sell signal present
   - ✅ Confluence ≥ 4/5
   - ✅ Clear TP/SL levels
   - ✅ Price inside NR range (optional)

### **3. Execution: Manual Trade**

1. Go to exchange (Binance, Bybit, etc.)
2. Set entry: Market order
3. Set TP: Limit order at predicted TP
4. Set SL: Stop-loss at predicted SL

### **4. Management:**

- Let trade run to TP or SL
- Don't move SL (stay disciplined)
- Track results in spreadsheet

---

## 🎛️ STRATEGY-SPECIFIC SETTINGS

### **Scalping (1m-15m)**

**Scanner Settings:**
- Pattern TF: 5m
- Signal TF: 1m
- Min ML Score: 65%
- Min Confluence: 3/5

**TradingView:**
- Strategy Mode: Scalping
- Timeframe: 1m or 5m
- Simple Mode: ON

**Trade Management:**
- TP: 1:1.2 (120 pips for every 100 risk)
- SL: 0.8% from entry
- Hold Time: 1-10 minutes
- Best Hours: High volatility (14:00-18:00 UTC)

### **Intraday (15m-4H)**

**Scanner Settings:**
- Pattern TF: 1h
- Signal TF: 15m
- Min ML Score: 70%
- Min Confluence: 4/5

**TradingView:**
- Strategy Mode: Intraday
- Timeframe: 1h
- Simple Mode: ON

**Trade Management:**
- TP: 1:2.0 (200 pips for every 100 risk)
- SL: 1.0% from entry
- Hold Time: 1-8 hours
- Best Setup: After NR pattern + breakout

### **Swing (4H-1W)**

**Scanner Settings:**
- Pattern TF: 1d
- Signal TF: 4h
- Min ML Score: 75%
- Min Confluence: 5/5

**TradingView:**
- Strategy Mode: Swing
- Timeframe: 1D
- Simple Mode: ON

**Trade Management:**
- TP: 1:3.5 (350 pips for every 100 risk)
- SL: 1.5% from entry
- Hold Time: Days to weeks
- Best Setup: NR10 on daily + all EMAs aligned

---

## 🔧 TROUBLESHOOTING

### **Scanner Issues:**

**Problem:** "ccxt not installed"
```bash
pip install ccxt
```

**Problem:** "ML Model not found"
```bash
# Train models first
python ml/collect_training_data.py --strategy intraday
python ml/train_models.py --strategy intraday
```

**Problem:** "No setups found"
- Lower Min ML Score to 60%
- Reduce Min Confluence to 3/5
- Check more coins
- Try different timeframes

**Problem:** "Exchange blocked (451)"
- Try different exchange in provider chain
- Use VPN if needed
- Or enable "UTC Fallback" for daily timeframe only

### **TradingView Issues:**

**Problem:** "Compilation error"
- Check you copied complete code
- Verify Pine Script version is v5
- No syntax errors in paste

**Problem:** "No signals showing"
- Disable Simple Mode temporarily
- Check if confluence ≥ min_confluence
- Verify indicators are enabled
- Check if NR pattern exists on Pattern TF

**Problem:** "Too many lines on chart"
- Enable Simple Mode
- Disable unused indicators in settings
- Focus on: NR, SuperTrend, EMAs only

---

## 📈 PERFORMANCE TRACKING

### **Recommended Spreadsheet Columns:**

```
Date | Coin | Strategy | Entry | TP | SL | ML Score | Confluence | Outcome | Profit% | Notes
```

### **Key Metrics to Track:**

- **Win Rate**: % of trades that hit TP
- **Avg R:R**: Average Risk:Reward
- **Best Strategy**: Which performs best for you
- **Best ML Score Range**: E.g., 80-90% scores best?
- **Best Confluence**: 4/5 vs 5/5 performance

### **Monthly Review:**

1. Calculate overall win rate
2. Compare to ML predictions
3. Adjust Min ML Score if needed
4. Identify best coins/timeframes
5. Re-train models with new data

---

## 🎓 ADVANCED: RE-TRAINING MODELS

### **When to Re-train:**

- Every 1-3 months
- After major market changes
- If win rate drops significantly
- When adding new strategies

### **How to Re-train:**

```bash
# 1. Collect fresh data
python ml/collect_training_data.py --strategy intraday

# 2. Combine with old data (optional)
# Manually merge CSVs in ml/data/ folder

# 3. Re-train
python ml/train_models.py --strategy intraday

# 4. Test
python ml/test_models.py --strategy intraday

# 5. If accuracy improved, use new model
# Otherwise, keep old model
```

---

## 📚 FILE STRUCTURE REFERENCE

```
merlin-trading-system/
├── merlin_scanner_ml.py          # Main scanner app
├── requirements.txt               # Python dependencies
├── merlin_matrix_v6_ml.pine      # TradingView indicator
│
├── ml/
│   ├── collect_training_data.py  # Data collection
│   ├── train_models.py           # Model training
│   ├── test_models.py            # Model testing
│   │
│   ├── data/                     # Training data
│   │   ├── training_data_scalping.csv
│   │   ├── training_data_intraday.csv
│   │   └── training_data_swing.csv
│   │
│   ├── models/                   # Trained models
│   │   ├── scalping_rf.pkl
│   │   ├── intraday_rf.pkl
│   │   └── swing_rf.pkl
│   │
│   └── plots/                    # Visualizations
│       └── *_feature_importance.png
│
└── docs/
    └── SETUP.md                  # This file
```

---

## 🎯 QUICK REFERENCE COMMANDS

```bash
# Installation
pip install -r requirements.txt

# Data Collection
python ml/collect_training_data.py --strategy all

# Model Training
python ml/train_models.py --strategy all

# Model Testing
python ml/test_models.py --strategy intraday

# Run Scanner
streamlit run merlin_scanner_ml.py
```

---

## 🆘 SUPPORT & RESOURCES

### **Common Questions:**

**Q: Can I use this for stocks/forex?**
A: Code is designed for crypto but adaptable. Change symbols and may need different features.

**Q: How accurate are ML predictions?**
A: Typically 60-70% accuracy. Not perfect, but better than random.

**Q: Can I automate trades?**
A: Yes, possible via exchange APIs, but start manual to learn system.

**Q: Which strategy is best?**
A: Intraday (1H) has best balance of opportunities and accuracy.

### **Next Steps:**

1. ✅ Set up scanner
2. ✅ Install TradingView indicator
3. ✅ Practice on paper trades
4. ✅ Track 20 trades
5. ✅ Review performance
6. ✅ Go live with small size
7. ✅ Scale up gradually

---

## 🧙‍♂️ FINAL TIPS

**From Merlin's Spellbook:**

1. **Trust the Process**: ML scores are probabilities, not guarantees
2. **Stay Disciplined**: Don't move SL, don't chase
3. **Track Everything**: Data = improvement
4. **Start Small**: Test with small position sizes
5. **Adapt**: Markets change, re-train models
6. **Confluence > ML Score**: 5/5 confluence beats 95% ML score
7. **Quality > Quantity**: Better to wait for perfect setup
8. **Simple Mode**: Less noise = better decisions
9. **Backtest First**: Paper trade before real money
10. **Never Stop Learning**: Review trades, improve system

**Remember:** *"The wand chooses the wizard, but the wizard chooses the strategy!"* 🪄

---

**Good luck, and may your trades be ever profitable!** 🚀📈

*— Merlin's ML Trading System v6.0*
