# TRADING FRAMEWORK - Backtesting Modulare in Python

## 🎯 COSA VOGLIAMO OTTENERE

Un sistema di backtesting **semplice, modulare e veloce** che permetta di:
1. **Scrivere strategie in pochi minuti** - senza boilerplate code
2. **Testare idee rapidamente** - con cache intelligente per performance
3. **Essere estensibile** - aggiungere indicatori, strategie, assets facilmente
4. **Avere dati strutturati** - journal completo per analisi post-trade
5. **Prepararsi al futuro** - architettura pronta per UI e trading live

**Filosofia:** La strategia è una **funzione pura** che dato un contesto di mercato (prezzi, indicatori) restituisce True/False. Tutto il resto (gestione denaro, posizioni, commissioni) è gestito dal framework.

## 🛠️ COME OTTENERE IL NOSTRO SCOPO

### Principi di Design:
1. **Separation of Concerns**: 
   - Strategia: solo logica True/False
   - Engine: gestione stato ed esecuzione
   - Data: formato standard (Parquet) con cache
2. **Configuration over Code**:
   - Tutto configurabile via `config.yaml`
   - Niente hardcoded parameters
3. **Cache First**:
   - Indicatori calcolati una volta, usati infinite volte
   - Performance istantanea dopo prima esecuzione
4. **Modularità**:
   - Entry/Exit strategie intercambiabili
   - Aggiungi indicatori senza modificare core
5. **Simple First**:
   - Inizia con funzionalità base
   - Estendi gradualmente

## 📋 FASI DI IMPLEMENTAZIONE

### **✅ FASE 1: FOUNDATION** (MINIMO FUNZIONANTE) - **COMPLETATA!**
- ✅ Struttura cartelle base
- ✅ `config.yaml` schema minimale
- ✅ Data loader per Parquet 1m
- ✅ 1 Indicatore base (SMA) con cache
- ✅ 1 Strategia entry semplice (price > SMA)
- ✅ 1 Strategia exit semplice (fixed bars)
- ✅ Engine loop base (senza risk management)
- ✅ Journal writer base (CSV semplice)
- ✅ Output console base

**Obiettivo raggiunto:** `python backtest.py` funziona e produce risultati base! 🎉

### **✅ FASE 2: CORE FEATURES** - **COMPLETATA!**
- ✅ Risk manager (position sizing) - `FixedPercentRisk`
- ✅ Commissioni e slippage
- ✅ **Journal in Parquet** (non CSV) - ottimizzazione performance
- ✅ **Metriche base avanzate** - detailed summary con verification
- ✅ **Grafico equity base** (matplotlib) - 3 tipi di plot
- ✅ Integration completa risk management nel engine

**Obiettivo raggiunto:** Framework stabile con risk management e visualizzazione! 📊

### **📋 FASE 3: DEBUG & STABILIZATION** (PROSSIMA)
- [ ] **Debug calcoli risk management** - verifica consistenza position sizing
- [ ] **Verifica precisione calcoli** - P&L, commissioni, equity
- [ ] **Controlli di consistenza** automatici nei risultati
- [ ] **Logging dettagliato** per debugging calcoli
- [ ] **Test suite base** per verificare componenti critici
- [ ] **Documentazione calcoli** - spiegazione formule usate

**🔍 NOTA CRITICA:** Durante i test sono state identificate possibili incongruenze nei calcoli di position sizing.
La FASE 3 focalizzerà sulla verifica e correzione di questi aspetti critici prima di aggiungere nuove feature.

### **📋 FASE 4: ENHANCED FEATURES** 
- [ ] Multi indicatori (EMA, RSI, ATR)
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support
- [ ] Multi-timeframe indicators
- [ ] Advanced risk metrics (Sharpe, Sortino, Calmar)
- [ ] Walk-forward testing
- [ ] Parameter optimization (grid search)

### **📋 FASE 5: PRODUCTION READY**
- [ ] Gestione errori robusta
- [ ] Validazione config e dati
- [ ] Logging strutturato
- [ ] Report HTML completo
- [ ] Script utilità (download data, cleanup)
- [ ] UI web (Streamlit)

### **📋 FASE 6: ADVANCED ECOSYSTEM**
- [ ] Plugin system per indicatori/strategie
- [ ] Cloud storage per dati/journal
- [ ] API REST per automazione
- [ ] Monte Carlo simulations
- [ ] Live trading bridge (futuro)
- [ ] Documentation completa

## 🔄 WORKFLOW DI SVILUPPO

Per ogni fase:
1. **Chat dedicata** su quella fase specifica
2. **Implementazione incrementale**:
   - Modifica `config.yaml` schema se necessario
   - Implementa feature in moduli isolati
   - Test con dati sample
   - Integra nel flow principale
3. **Update documentation**:
   - Aggiorna `readme.md` con progressi
   - Documenta nuove feature
   - Aggiorna esempi
4. **Verifica consistenza**:
   - Tutti i moduli lavorano insieme
   - Cache funziona correttamente
   - Output è come atteso

## 📁 STRUTTURA CHIAVE (riassunto)

```txt
trading_framework/
├── config.yaml # CENTRO DI CONTROLLO
├── backtest.py # PUNTO DI INGRESSO
├── core/ # Motore (modificare raramente)
│   ├── data_loader.py
│   ├── data_window.py
│   ├── engine.py
│   ├── indicator_manager.py
│   └── journal_writer.py
├── strategies/ # Logica trading (modificare spesso)
│   ├── entry/
│   │   ├── base_entry.py
│   │   └── price_above_sma.py
│   ├── exit/
│   │   ├── base_exit.py
│   │   ├── hold_bars.py
│   │   └── fixed_tp_sl.py
│   └── risk/
│       ├── base_risk.py
│       └── fixed_percent.py
├── indicators/ # Calcoli indicatori
│   ├── base_calculator.py
│   └── sma_calculator.py
├── reports/ # Visualizzazioni
│   ├── plotter.py
│   └── __init__.py
├── data/ # Dati e cache (NON versionare)
└── results/ # Output backtest
```

## 🚀 COMINCIARE

### Prerequisiti:

```bash
Python 3.9+
pip install -r requirements.txt

# Per TA-Lib:
# Ubuntu/Debian: sudo apt-get install libta-lib-dev
# macOS: brew install ta-lib
# Poi: pip install TA-Lib

# Per visualizzazioni (FASE 2+):
pip install matplotlib
```

### Passo 1 - Setup dati:
```bash
# Metti i tuoi dati 1m in data/raw/BTCUSDT-1m-*.parquet
```

### Passo 2 - Configura `config.yaml`:
```yaml
data:
  symbols: ["BTCUSDT"]
  timeframe: "1m"
  
strategy:
  entry:
    name: "price_above_sma"
    params: {period: 20, lookback: 1}
  exit:
    name: "hold_bars"
    params: {bars: 10}
  risk:  # Nuovo in FASE 2
    name: "fixed_percent"
    params: {risk_per_trade: 0.02}

indicators:
  - name: "sma"
    params: {period: 20}
    tf: "1m"
    column: "sma_20"
```

### Passo 3 - Esegui backtest:
```bash
python backtest.py
```

### Passo 4 - Analizza risultati:
- Console: Summary dettagliato
- `results/`: Files Parquet + PNG con grafici
- `data/indicators/`: Cache indicatori (riutilizzabile - formato parquet)

## 🎯 ESEMPIO DI OUTPUT FASE 2

```txt
================================================================================
BACKTEST SUMMARY - Detailed Performance Report
================================================================================

📈 CORE PERFORMANCE METRICS:
------------------------------------------------------------
Initial Capital:          $10,000.00
Final Equity:             $5,278.06
Total Return:             -47.22%

Gross P&L (pre-costs):    $+40.91
Total Costs:              $4,763.91
Net P&L (after costs):    $-4723.00

📊 RISK & DRAWDOWN METRICS:
------------------------------------------------------------
Maximum Drawdown:         47.22%
Drawdown Level:          ⚠️  Extreme (>30%)

🎯 TRADE STATISTICS:
------------------------------------------------------------
Total Trades:             1613
Winning Trades:           144 (8.9%)
Losing Trades:            1469 (91.1%)
Profit Factor:            1.03
Average P&L/Trade:        $-2.93

⚖️  RISK MANAGEMENT:
------------------------------------------------------------
Risk Manager:             FixedPercentRisk (2.0% risk per trade)
Avg Commission per Trade: $2.95

💡 EXECUTIVE SUMMARY:
------------------------------------------------------------
😔 STRATEGY UNPROFITABLE
⚠️  EXTREME RISK: Drawdown >30%
⚡ HIGH FREQUENCY: >10 trades/day

🎯 RECOMMENDATIONS:
------------------------------------------------------------
❌ REJECT: Unprofitable with extreme drawdown
```

## 📈 VISUALIZZAZIONI DISPONIBILI (FASE 2)

Il framework ora genera automaticamente 3 grafici PNG:

1. **`equity_curve.png`** - Equity curve con drawdown
2. **`trade_distribution.png`** - Distribuzione P&L, trade cumulativo, exit reasons
3. **`price_signals.png`** - Prezzi con entry/exit markers e position status

## 🐛 NOTE SU CALCOLI (DA VERIFICARE IN FASE 3)

Durante i test sono state osservate potenziali incongruenze nei calcoli:
- Position sizing potrebbe non rispettare esattamente il `risk_per_trade` configurato
- Piccole discrepanze nei calcoli di P&L (~0.02%)
- Verificare consistenza tra calcoli nel log e nel summary

**La FASE 3 si concentrerà sulla risoluzione di queste potenziali issue critiche.**

## 📝 NOTE PER LO SVILUPPO

**Priorità:**
1. Funziona → Corretto → Veloce → Bello
2. Iniziare con esempi minimi funzionanti
3. Testare ogni componente isolatamente
4. Mantenere backward compatibility

**Mantra:** "Scrivi strategie, non boilerplate"

## 🎯 DECISIONI ARCHITETTURALI:

- **Parquet over CSV/DB**: performance, compression, schema evolution
- **YAML over JSON/INI**: human readable, commenti, gerarchia
- **Classi over functions**: per strategie, ma interfacce semplici
- **Cache on disk**: tra esecuzioni, non solo in memoria

## 📊 PERFORMANCE ATTUALI:

- **Prima esecuzione**: ~2-60s (calcolo indicatori)
- **Esecuzioni successive**: ~5s (tutto in cache)
- **Formato dati**: Parquet (veloce, compresso)
- **Visualizzazioni**: Matplotlib PNG (compatto, universale)

## 🔧 COME AGGIUNGERE NUOVE FEATURES:

### Nuovo risk manager:
1. Crea `strategies/risk/nome_manager.py`
2. Estendi `BaseRiskManager`
3. Implementa `calculate_position_size()`
4. Aggiungi a `config.yaml` sezione `strategy.risk`

### Nuovo plot type:
1. Crea metodo in `reports/plotter.py`
2. Aggiungi a `create_all_plots()`
3. Il `JournalWriter` lo includerà automaticamente

## 🎉 SUCCESSO FASE 2!

La FASE 2 è stata completata con successo! Abbiamo aggiunto:

1. ✅ **Risk management** con position sizing intelligente
2. ✅ **Output Parquet** per performance ottimali
3. ✅ **Metriche avanzate** con verification automatica
4. ✅ **Visualizzazioni** con matplotlib
5. ✅ **Framework stabile** e pronto per debug

**Prossimi passi:** FASE 3 - Debug e stabilizzazione dei calcoli critici!

*Documentazione creata il: 2024-01-16*
*Ultimo aggiornamento: 2024-01-16 - FASE 2 COMPLETATA! 🎉*
*Stato: PRONTO PER FASE 3 - DEBUG & STABILIZATION*
[file content end]


## ✅ **AGGIORNAMENTO COMPLETATO!**

Ora il `readme.md` riflette accuratamente:

1. **✅ FASE 2 COMPLETATA** con tutti gli elementi realizzati
2. **📋 FASE 3 DEFINITA** come "Debug & Stabilization"
3. **🔍 NOTA CRITICA** evidenziata per le incongruenze nei calcoli
4. **📋 FASE 4** dove spostiamo indicatori multipli e strategie multiple
5. **Struttura aggiornata** con tutte le nuove componenti (risk/, reports/)

**Pronti per iniziare la FASE 3 quando vuoi!** 🛠️