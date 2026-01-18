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
- ✅ **Fix output directory** -> Must be taken from config
- ✅ **Debug calcoli risk management** - verifica consistenza position sizing
- ✅ **Verifica precisione calcoli** - P&L, commissioni, equity
- ✅ **Controlli di consistenza** automatici nei risultati
- ✅ **Logging dettagliato** per debugging calcoli
- ✅ **Documentazione calcoli** - spiegazione formule usate -> In english! -> Suggest a name for the document


### **📋 FASE 4: ENHANCED FEATURES** 
- [ ] Multi indicatori (EMA, RSI, ATR)
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support
- [ ] Multi-timeframe indicators
- [ ] Advanced risk metrics (Sharpe, Sortino, Calmar)
- [ ] Walk-forward testing
- [ ] Monte Carlo simulations
- [ ] Parameter optimization (grid search)

### **📋 FASE 5: PRODUCTION READY**
- [ ] Gestione errori robusta
- [ ] Validazione config e dati
- [ ] Logging strutturato
- [ ] Report HTML completo
- [ ] Script utilità (download data, cleanup)
- [ ] BASIC UI web (Streamlit)

### **📋 FASE 6: ADVANCED ECOSYSTEM**
- [ ] Plugin system per indicatori/strategie
- [ ] Cloud storage per dati/journal
- [ ] API REST per automazione
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
├── data/ # Dati e cache (NON versionare) // No hardcode -> Preso da config.yaml
└── results/ # Output backtest // No hardcode -> Preso da config.yaml
```



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

- **Parquet (and CSV/DB if required)**: performance, compression, schema evolution
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

