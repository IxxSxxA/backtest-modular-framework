# STRUTTURA DEL PROGETTO

## 📁 Organizzazione File e Cartelle


```txt
trading_framework/
│
├── 📁 data/ # TUTTI i dati (NON versionato su git)
│ ├── 📁 raw/ # Dati grezzi da exchange
│ │ ├── BTCUSDT_1m.parquet # Formato: {SYMBOL}{TIMEFRAME}.parquet
│ │ ├── ETHUSDT_1m.parquet
│ │ └── .gitkeep
│ │
│ ├── 📁 indicators/ # Indicatori precalcolati (cache organizzata)
│ │ ├── BTCUSDT/ # Cartella per symbol
│ │ │ ├── sma_20_1m.parquet # Formato: {INDICATOR}{PARAMS}_{TF}.parquet
│ │ │ ├── rsi_14_1m.parquet
│ │ │ └── ema_50_1h.parquet
│ │ ├── ETHUSDT/
│ │ │ └── ...
│ │ └── .gitkeep
│ │
│ ├── 📁 journals/ # Journal dei backtest completi
│ │ ├── BTCUSDT_ema_cross_fixed_tp_sl_20250116_143025.parquet
│ │ ├── ETHUSDT_rsi_oversold_trailing_20250116_143030.parquet
│ │ └── .gitkeep
│ │
│ └── 📁 strategy_ready/ # Dataset pronti per strategie (merge finale)
│ └── .gitkeep
│
├── 📁 core/ # CODICE CORE (non modificare spesso)
│ ├── init.py
│ ├── engine.py # BacktestEngine principale
│ ├── indicator_manager.py # Gestione cache indicatori intelligente
│ ├── journal_writer.py # Scrittura journal in parquet
│ ├── risk_manager.py # Gestione rischio e position sizing
│ └── data_loader.py # Caricamento/aggregazione dati multi-TF
│
├── 📁 strategies/ # STRATEGIE (qui lavori sempre)
│ ├── 📁 entry/ # Strategie di ENTRY (True/False)
│ │ ├── init.py
│ │ ├── base_entry.py # Classe base astratta
│ │ ├── ema_cross.py # Esempio: Cross EMA veloce/lenta
│ │ ├── rsi_oversold.py # Esempio: RSI < 30
│ │ └── bollinger_squeeze.py # Esempio: Bande di Bollinger
│ │
│ ├── 📁 exit/ # Strategie di EXIT -> SONO TUTTE TP/SL (True/False + motivo)
│ │ ├── init.py
│ │ ├── base_exit.py # Classe base astratta
│ │ ├── fixed_tp_sl.py # Take Profit / Stop Loss fissi
│ │ ├── trailing_stop.py # Trailing stop dinamico
│ │ ├── time_based.py # Exit dopo N candele
│ │ └── atr_stop.py # Stop basato su ATR
│ │
│ └── 📁 risk/ # Gestione rischio - Quanto capitale
│ ├── init.py
│ ├── base_risk.py
│ ├── fixed_percent.py # Rischia X% per trade
│ └── kelly_criterion.py # Criterio di Kelly
│
├── 📁 indicators/ # CALCOLATORI indicatori (estensibili)
│ ├── init.py
│ ├── base_calculator.py # Classe base per indicatori
│ ├── sma_calculator.py # Simple Moving Average
│ ├── ema_calculator.py # Exponential Moving Average
│ ├── rsi_calculator.py # Relative Strength Index
│ ├── macd_calculator.py # MACD
│ ├── bollinger_calculator.py # Bollinger Bands
│ ├── cvd_calculator.py # Cumulative Volume Delta
│ └── atr_calculator.py # Average True Range
│
├── 📁 utils/ # Utilities e helper functions
│ ├── init.py
│ ├── time_utils.py # Conversione timeframe, calcoli date
│ ├── file_utils.py # Gestione file parquet, cache
│ ├── validation.py # Validazione config e dati
│ └── logging_config.py # Configurazione logging strutturato
│
├── 📁 reports/ # Generazione report e visualizzazione
│ ├── init.py
│ ├── metrics_calculator.py # Sharpe, drawdown, win rate, etc.
│ ├── plotter.py # Creazione grafici (equity, drawdown)
│ ├── html_report.py # Generazione report HTML
│ └── 📁 templates/ # Template per report
│ └── report_template.html
│
├── 📁 scripts/ # Script standalone per operazioni
│ ├── download_data.py # Scarica dati da exchange
│ ├── calculate_indicators.py # Calcola tutti indicatori (batch)
│ ├── cleanup_cache.py # Pulisce cache vecchia
│ └── optimize_strategy.py # Ottimizzazione parametri (futuro)
│
├── 📁 ui/ # INTERFACCIA WEB (futuro, opzionale)
│ ├── init.py
│ ├── app.py # Streamlit/Dash app principale
│ ├── 📁 components/ # Componenti UI riutilizzabili
│ │ ├── strategy_builder.py
│ │ ├── param_controls.py
│ │ └── results_display.py
│ └── 📁 assets/ # Risorse statiche
│ └── style.css
│
├── 📄 config.yaml # CONFIGURAZIONE PRINCIPALE (modificare sempre qui)
├── 📄 backtest.py # PUNTO DI INGRESSO principale
├── 📄 requirements.txt # Dipendenze Python (pandas, pyarrow, talib, yaml)
├── 📄 .gitignore # Ignora data/, pycache/, .parquet
├── 📄 README.md # Documentazione utente
└── 📄 .env.example # Variabili d'ambiente esempio (API keys)
```


## 📄 Convenzioni di Nomenclatura File

### File Dati:
- **Raw data**: `{SYMBOL}_{TIMEFRAME}.parquet` (es: `BTCUSDT_1m.parquet`)
- **Indicator cache**: `{INDICATOR}_{PARAMS}_{TF}.parquet` (es: `sma_20_1m.parquet`)
- **Journal**: `{SYMBOL}_{ENTRY_STRAT}_{EXIT_STRAT}_{TIMESTAMP}.parquet`
- **Results**: `{SYMBOL}_{ENTRY_STRAT}_{EXIT_STRAT}_{TIMESTAMP}/`

### File Codice:
- **Strategie entry**: `strategies/entry/{nome_strategia}.py`
- **Strategie exit**: `strategies/exit/{nome_strategia}.py`
- **Indicatori**: `indicators/{nome_indicatore}_calculator.py`

## 🔧 Dipendenze Principali
- `pandas` - Manipolazione dati
- `pyarrow` - Lettura/scrittura parquet
- `TA-Lib` - Indicator calculation
- `PyYAML` - Lettura configurazione
- `numpy` - Calcoli numerici

## 🚫 Cosa NON è Incluso
- Database complessi (solo file parquet)
- Microservizi (monolito organizzato)
- Over-engineering (solo ciò che serve)