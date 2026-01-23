# 📚 TRADING FRAMEWORK - Quick Start Guide

## 🎯 Filosofia del Framework

**Principio base:** La strategia è una **funzione pura** che dato un contesto di mercato (prezzi, indicatori) restituisce True/False per entry/exit. Tutto il resto (gestione denaro, posizioni, commissioni) è gestito dal framework.

**Separazione dei compiti:**
- **Strategia:** Solo logica di trading (QUANDO comprare/vendere)
- **Engine:** Gestione stato, capitale, posizioni
- **Indicatori:** Pre-calcolati e cached (performance istantanea)
- **Config:** Tutto configurabile via YAML (zero hardcoded params)

---

## 📁 Struttura File

```
project/
├── config.yaml              # ← TUTTO parte da qui
├── data/
│   ├── raw/                 # Dati 1m parquet
│   ├── indicators/          # Cache indicatori (auto-generati)
│   ├── journals/            # Risultati backtest
│   └── plots/               # Grafici
├── core/
│   ├── engine.py            # Motore backtest
│   ├── data_loader.py       # Carica dati parquet
│   └── indicator_manager.py # Calcola/cache indicatori
├── strategies/
│   ├── entry/               # Strategie entry
│   ├── exit/                # Strategie exit
│   └── risk/                # Risk management
└── indicators/
    └── *_calculator.py      # Calcolatori indicatori
```

---

## ⚙️ Config.yaml - La Mappa del Backtest

```yaml
# === BACKTEST PERIOD ===
backtest:
  period:
    start: "2026-01-10"
    end: "2026-01-22"
  capital:
    initial: 10000
  costs:
    commission: 0.001

# === DATA SOURCE ===
data:
  symbols: ["XPLUSDT"]
  timeframe: "1m"                              # ✅ RAW data sempre 1m
  source_dir: "data/raw"
  source_file: "XPLUSDT-1m-2025-2026-01-22"   # senza .parquet

# === STRATEGY ===
strategy:
  timeframe: "4h"                              # ✅ TF della strategia
  
  entry:
    name: "price_above_sma"
    params:
      sma_column: "sma_200"                    # ✅ Referenzia indicatore
      lookback: 1
  
  exit:
    name: "hold_bars"
    params:
      bars: 100
  
  risk:
    name: "fixed_percent"
    params:
      risk_per_trade: 0.02

# === INDICATORS ===
indicators:
  - name: "sma"
    params: {period: 200}
    column: "sma_200"                          # ✅ Nome colonna

# === OUTPUT ===
output:
  journal:
    save_dir: "data/journals/"
  plots:
    enabled: true
    overlays:
      - column: "sma_200"
        color: "#ff0000"
```

---

## 🔄 Come Funziona il Flusso

### 1. **Data Loading**
```python
# data_loader.py
data = pd.read_parquet(f"{source_dir}/{source_file}.parquet")
# → DataFrame 1m grezzo
```

### 2. **Resampling a Strategy TF**
```python
# indicator_manager.py
data_4h = resample_to_timeframe(data_1m, "4h")  # Forward-fill
# → DataFrame 4h allineato
```

### 3. **Indicator Calculation con Cache**
```python
# Per ogni indicatore in config.yaml
sma_200 = SMACalculator().calculate_with_cache(data_4h, {period: 200})
# → Salvato in data/indicators/XPLUSDT/sma_period200_4h_hash.parquet
# → Prossima run: istantaneo!
```

### 4. **Strategy Execution**
```python
# engine.py
for bar in data_4h:
    if entry_strategy.should_enter(data):  # Accesso: data['sma_200'][0]
        enter_position()
    if exit_strategy.should_exit(data):
        exit_position()
```

### 5. **Results Output**
```
data/journals/XPLUSDT_4h_price_above_sma_20260122_143022/
├── metrics.json          # Metriche aggregate
├── trades.parquet        # Lista trade
├── journal.parquet       # Tick-by-tick log
├── equity_curve.png      # Grafico equity
└── price_signals.png     # Grafico prezzi + indicatori
```

---

## 🚀 Quick Start (3 passi)

### 1. Prepara Dati
```bash
# Metti file parquet 1m in data/raw/
data/raw/XPLUSDT-1m-2025-2026-01-22.parquet
```

### 2. Configura
```yaml
# config.yaml
data:
  source_file: "XPLUSDT-1m-2025-2026-01-22"
strategy:
  timeframe: "4h"
```

### 3. Run
```bash
python main.py
```

**Output:** Risultati in `data/journals/[ultima_cartella]/`

---

## 🔑 Concetti Chiave

### **Timeframes**
- `data.timeframe: "1m"` → Dati raw (sempre 1m)
- `strategy.timeframe: "4h"` → TF strategia (controlla tutto)
- Indicatori calcolati su strategy TF automaticamente

### **Indicator Caching**
- **Prima run:** Calcola e salva → ~5 sec
- **Run successive:** Carica da cache → <0.1 sec
- Cache invalidata se cambiano parametri

### **Strategy Reference**
```yaml
entry:
  params:
    sma_column: "sma_200"  # ✅ Referenzia nome colonna
    
indicators:
  - column: "sma_200"      # ✅ Single source of truth
    params: {period: 200}
```

### **Data Window Access**
```python
# Nella strategia
data['close'][0]      # Prezzo corrente
data['close'][-1]     # Prezzo precedente
data['sma_200'][0]    # SMA corrente
data['sma_200'][-5]   # SMA 5 bar fa
```

---

## ❓ FAQ Rapide

**Q: Dove trovo il file da caricare?**  
A: `data.source_dir` + `data.source_file` + `.parquet`

**Q: Come cambio TF strategia?**  
A: `strategy.timeframe: "1h"` (supporta 1m, 5m, 15m, 1h, 4h, 1d)

**Q: Come aggiungo un indicatore?**  
A: Aggiungi in `indicators:` sezione config, verrà auto-calcolato

**Q: Devo ricalcolare indicatori se cambio strategia?**  
A: No! Cache riutilizzata se stessi parametri

**Q: Come vedo risultati?**  
A: `data/journals/[ultima_cartella]/summary.txt` + grafici PNG

---

## 🎯 Prossimi Sviluppi (Future Phases)

- ⏳ Multi-timeframe strategies
- 📊 Multi-symbol portfolio
- 💧 Slippage simulation
- 🔄 Walk-forward optimization
- 🌐 Live trading connector

---

**Mantieni semplice. Testa veloce. Itera spesso.** 🚀