# PIPELINE ESECUTIVA - Flusso di Backtest

## 🔄 FLUSSO COMPLETO (Single o Multi-Asset)

```txt
[UTENTE] → python backtest.py
↓
[FASE 1: CONFIGURAZIONE]
├─ Legge config.yaml
├─ Valida tutti i parametri
├─ Carica classi strategia (entry/exit)
└─ Se errore → STOP con messaggio chiaro
↓
[FASE 2: PREPARAZIONE DATI] (Per ogni symbol in config['symbols'])
├─ Carica: data/raw/{SYMBOL}{TIMEFRAME}.parquet
├─ Filtra date (start/end da config)
├─ Calcola/recupera indicatori (cache intelligente)
│ ├─ Se esiste: data/indicators/{SYMBOL}/{INDICATOR}{PARAMS}.parquet → carica
│ └─ Se non esiste: calcola → salva cache → carica
└─ Merge: OHLCV + tutti indicatori → dataset completo
↓
[FASE 3: INIZIALIZZAZIONE ENGINE]
├─ Crea BacktestEngine con:
│ ├─ Dataset completo
│ ├─ Entry strategy (da config)
│ ├─ Exit strategy (da config)
│ ├─ Parametri rischio/commissioni
│ └─ Stato iniziale (capitale, posizioni)
└─ Inizializza journal writer
↓
[FASE 4: BACKTEST LOOP] (Per ogni candela, timestamp ordinati)
│
├─ [4.1: ENTRY CHECK] Se NON in posizione:
│ ├─ Chiama: entry_strategy.should_enter(current_data_window)
│ └─ Se True → Engine.enter_position():
│ ├─ Calcola position size (risk manager)
│ ├─ Registra entry price/time
│ ├─ Aggiorna stato portfolio
│ └─ Log: "ENTER at {price}"
│
├─ [4.2: EXIT CHECK] Se IN posizione:
│ ├─ Chiama: exit_strategy.should_exit(current_data_window, entry_price)
│ └─ Se True → Engine.exit_position():
│ ├─ Calcola P&L realizzato
│ ├─ Applica commissioni
│ ├─ Aggiorna capitale
│ ├─ Registra trade completo
│ └─ Log: "EXIT at {price}, P&L: {X}%"
│
└─ [4.3: JOURNAL WRITING] Per ogni candela:
├─ Scrive riga in: data/journals/{SYMBOL}{STRAT}{TIMESTAMP}.parquet
└─ Campi: timestamp, symbol, price, signals, position, capital, indicators*
↓
[FASE 5: POST-PROCESSING]
├─ Chiudi eventuali posizioni aperte (alla fine periodo)
├─ Calcola metriche performance:
│ ├─ Total Return %
│ ├─ Sharpe Ratio
│ ├─ Max Drawdown %
│ ├─ Win Rate %
│ ├─ Profit Factor
│ └─ Numero trades
└─ Genera output strutturato
↓
[FASE 6: OUTPUT & VISUALIZATION]
├─ Stampa summary a schermo
├─ Salva file risultati:
│ ├─ Trades CSV: results/{SYMBOL}{STRAT}{TIMESTAMP}/trades.csv
│ ├─ Equity curve: results/{SYMBOL}{STRAT}{TIMESTAMP}/equity.png
│ ├─ Report HTML: results/{SYMBOL}{STRAT}{TIMESTAMP}/report.html
│ └─ Metrics JSON: results/{SYMBOL}{STRAT}{TIMESTAMP}/metrics.json
└─ Se UI attiva → aggiorna dashboard live
↓
[FINE] ✅ Backtest completato
```

## ⏱️ TIMELINE TIPICA (525k candele 1m = 1 anno)

### Prima Esecuzione (indicatori da calcolare):
T+0s: python backtest.py
T+1s: Config loaded ✓
T+2s: Data loaded (525k candles) ✓
T+2-60s: Calculating indicators... (dipende da quanti e complessità)
T+60s: Starting backtest loop...
T+180s: [===============>] 100% (2,900 candles/sec)
T+181s: Calculating metrics...
T+182s: Generating plots...
T+185s: ✅ Backtest completed!



### Esecuzioni Successive (tutto in cache):
T+0s: python backtest.py
T+1s: Config loaded ✓
T+2s: Data + indicators from cache ✓
T+3s: Backtest loop (525k candles in 2s)
T+5s: ✅ Backtest completed! (5 secondi totali)



## 🎯 INPUT/OUTPUT CHIAVE

### INPUT (config.yaml):

```yaml
symbols: ["BTCUSDT", "ETHUSDT"]      # Assets da testare
timeframe: "1m"                      # TF del motore
strategy:
  entry:
    name: "ema_cross"               # File: strategies/entry/ema_cross.py
    params: {fast: 20, slow: 50}    # Parametri strategia
  exit:
    name: "fixed_tp_sl"             # File: strategies/exit/fixed_tp_sl.py
    params: {tp: 0.05, sl: 0.02}    # TP 5%, SL 2%
indicators:                         # Lista indicatori richiesti
  - sma_20_1m
  - rsi_14_1m
  - ema_50_4h
```

### OUTPUT (per symbol):

```text
data/journals/BTCUSDT_ema_cross_fixed_tp_sl_20250116_143025.parquet
├── 525,600 righe (1 riga per candela 1m)
├── Colonne: timestamp, symbol, price, entry_signal, exit_signal, 
│           in_position, position_size, capital, drawdown, 
│           ema_fast, ema_slow, rsi, ... (tutti indicatori)
└── Formato: Parquet (veloce, compresso)

results/BTCUSDT_ema_cross_fixed_tp_sl_20250116_143025/
├── trades.csv           # Lista trade con P&L
├── equity.png          # Grafico equity curve
├── drawdown.png        # Grafico drawdown
├── report.html         # Report HTML interattivo
└── metrics.json        # Metriche in formato JSON
```

## 🔄 CACHE INTELLIGENTE

Indicator calculation flow:
1. Riceve richiesta: "sma_20_1m" per "BTCUSDT"
2. Cerca: data/indicators/BTCUSDT/sma_20_1m.parquet
3. Se TROVATO: carica e restituisce (instant)
4. Se NON TROVATO:
   ├─ Calcola SMA(20) su dati 1m
   ├─ Salva: data/indicators/BTCUSDT/sma_20_1m.parquet
   └─ Restituisce risultato
5. Cache valida finché dati raw non cambiano
   (controllo tramite hash o timestamp ultima modifica)


## 🚨 GESTIONE ERRORI

Errori comuni e recovery:
1. File dati non trovato → "Esegui scripts/download_data.py"
2. Strategia non trovata → "Crea strategies/entry/{nome}.py"
3. Indicatore non implementato → "Crea indicators/{nome}_calculator.py"
4. Cache corrupted → "Esegui scripts/cleanup_cache.py"
5. Config invalido → Messaggio con campo problematico


## 📈 SCALABILITÀ

Da Single a Multi-Asset:
1. Single: symbols: ["BTCUSDT"]
2. Multi: symbols: ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
3. Cross-asset: (futuro) strategie che confrontano assets

Da 1 a N Timeframe:
1. Base: timeframe: "1m"
2. Multi-TF: indicatori su TF diversi (sma_20_5m, ema_50_1h)
3. Strategie multi-TF: entry su 5m, exit su 15m


## 🎨 VISUALIZATION PIPELINE (Futuro)

Journal Parquet → Plotter → Visualizations:
1. Legge: data/journals/{SYMBOL}_{STRAT}_{TIMESTAMP}.parquet
2. Aggrega al TF per plotting (1m → 1h per equity curve)
3. Genera:
   - Equity curve con drawdown
   - Entry/exit points su grafico prezzi
   - Distribuzione P&L
   - Heatmap performance temporale
4. Output: PNG, HTML interattivo, PDF report
