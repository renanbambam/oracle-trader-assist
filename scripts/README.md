# MT5 Bridge

Script Windows-nativo que conecta ao MetaTrader5 e envia preços ao Oracle em tempo real.

## Pré-requisitos

- Windows 10/11 com MetaTrader5 instalado e aberto
- Python 3.10+ (fora do Docker)
- Oracle rodando em `http://localhost:8000`

## Instalação

```bash
pip install MetaTrader5 requests
```

## Configuração

Copie as variáveis do seu `.env` ou defina via terminal antes de rodar:

| Variável | Padrão | Descrição |
|---|---|---|
| `ORACLE_URL` | `http://localhost:8000` | URL base do servidor Oracle |
| `MT5_LOGIN` | — | Número da conta MT5 |
| `MT5_PASSWORD` | — | Senha da conta MT5 |
| `MT5_SERVER` | — | Nome do servidor (ex: `ActivTradesCorp-Server`) |
| `POLL_INTERVAL` | `5` | Intervalo de envio em segundos |

Se `MT5_LOGIN` não for definido, o bridge usa a sessão já ativa no terminal.

## Execução

Na raiz do projeto:

```bash
# Windows PowerShell
$env:MT5_LOGIN="YOUR_MT5_LOGIN"
$env:MT5_PASSWORD="sua_senha"
$env:MT5_SERVER="ActivTradesCorp-Server"
python scripts/mt5_bridge.py
```

Ou com variáveis inline:

```bash
MT5_LOGIN=YOUR_MT5_LOGIN MT5_PASSWORD=suasenha MT5_SERVER=ActivTradesCorp-Server python scripts/mt5_bridge.py
```

## Como funciona

```
MetaTrader5 (Windows)
        ↓  symbol_info_tick()
  mt5_bridge.py
        ↓  POST /api/v1/market/ingest
  Oracle (Docker/local)
        ↓  Redis publish
  WebSocket → Frontend ticker strip
```

1. O bridge conecta ao MT5 via `MetaTrader5.initialize()`
2. A cada `POLL_INTERVAL` segundos, faz `symbol_info_tick()` para cada símbolo
3. Envia `{symbol, price, bid, ask, spread, volume, timestamp}` para `POST /api/v1/market/ingest`
4. O Oracle armazena em Redis e publica no canal `market` via EventBus
5. O frontend recebe via WebSocket (`market.ticker_updated`) e atualiza ticker strip, cards e widget MT5

## Symbols configurados

- `PETR4`, `VALE3`, `WINQ25`, `DOLFUT` (B3)
- `EURUSD`, `XAUUSD`, `US100`, `USDJPY` (Forex/índices)

Para adicionar símbolos, edite a lista `SYMBOLS` em `scripts/mt5_bridge.py`.

## Sem MT5 disponível?

Se o MT5 não estiver disponível, o Oracle usa automaticamente o `MockMarketAdapter` para popular o frontend via `GET /api/v1/market/quotes`, chamado a cada 10 segundos pelo browser.
