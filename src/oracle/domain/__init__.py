"""Domain layer — pure business logic.

Contains: entities, value objects, domain services, repository interfaces.
No framework dependencies. No infrastructure imports.

Bounded contexts:
  market/    — OHLCV, ticker, market snapshots
  analysis/  — AI analysis, confidence scoring, multi-timeframe
  trade/     — trade journal, risk management, anti-FOMO
  memory/    — context sessions, conversation history
  replay/    — timeline, playback, frame annotations
  analytics/ — performance metrics, behavioural analysis
"""
