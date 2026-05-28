"""Application layer — use cases and orchestration.

Contains: use cases, application services, DTOs.
Depends on: domain layer.
Never imports from: infrastructure, interface.

Use cases per bounded context:
  analysis/  — RunAnalysis, SendMessage, ScoreSetup
  trade/     — RecordTrade, CloseTrade, ReflectOnTrade, RunChecklist
  memory/    — LoadContext, SaveContext, SearchHistory
  replay/    — CreateReplay, ControlReplay, AnnotateFrame
  analytics/ — GetPerformance, GetSetupStats
  briefing/  — GenerateBriefing
"""
