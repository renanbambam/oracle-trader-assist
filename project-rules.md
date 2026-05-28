# Oracle Trader Assist — Project Rules

## Naming Rules

- Use "Oracle Trader Assist" as official project name
- Internal service naming: `oracle_*` prefix
- Class naming: `Oracle*` prefix where applicable
- **Prohibited:** ~~Jarvis~~, ~~jarvis~~, ~~JARVIS~~

---

## Backend Philosophy

- **modular-first** — every design decision starts with modularity
- **maintainability-first** — code is written to be maintained, not just executed
- **testability-first** — if it's hard to test, the design is wrong
- **readability-first** — humans and AI must navigate the code without friction
- backend-first — no frontend before the core is solid
- API-first — contracts before implementations

---

## Modularidade

- Cada arquivo tem **responsabilidade única e bem definida**
- Preferir **composição** ao invés de centralização
- Alta coesão dentro de módulos; baixo acoplamento entre módulos
- Evitar arquivos "faz tudo" — se um arquivo responde a múltiplas questões, deve ser dividido
- Módulos são descobertos por nome — nomes devem comunicar intenção completa
- Nunca criar `utils.py`, `helpers.py` ou `misc.py` genéricos

---

## Limite de Complexidade

- **Alvo médio:** até ~200 linhas por arquivo
- **Limite real:** arquivos acima de ~300 linhas devem ser reconsiderados e provavelmente divididos
- Evitar classes "god object" com múltiplas responsabilidades
- Evitar services que acumulam lógica de bounded contexts diferentes
- Evitar routers gigantes — responsabilidade de routing apenas, sem lógica
- Evitar orchestrators monolíticos — quebrar em use cases individuais, um por arquivo

---

## Estrutura de Arquivos por Camada

### Domain — decomposição por tipo de conceito

```
domain/<context>/
├── entities.py       # Entidades (identidade, ciclo de vida)
├── value_objects.py  # Value objects (imutáveis, sem identidade)
├── enums.py          # Enumerações do domínio
├── events.py         # Eventos de domínio emitidos por este contexto
├── contracts.py      # Interfaces / Protocols (repositórios, providers)
└── services.py       # Domain services (lógica pura, sem IO)
```

### Application — um arquivo por use case

```
application/<context>/
├── dtos.py                  # Input/output DTOs do contexto
└── <use_case_name>.py       # Um único use case por arquivo
```

### Infrastructure — um arquivo por adapter/repositório

```
infrastructure/<adapter_type>/
├── <entity>_model.py        # ORM model (separado da entidade de domínio)
├── <context>_repository.py  # Implementação concreta do repositório
└── <provider>_adapter.py    # Adapter para serviço externo
```

### Interface — separar routing, requests e responses

```
interface/api/routers/<context>/
├── router.py        # FastAPI router — routing e delegates apenas
├── requests.py      # Schemas Pydantic de request
└── responses.py     # Schemas Pydantic de response
```

---

## Clean Architecture

- Dependências apontam **para dentro**: `interface → application → domain ← infrastructure`
- `domain` nunca importa de `infrastructure`, `interface` ou `application`
- `application` nunca importa de `interface`
- Interfaces/Protocols definidos no `domain`; implementações na `infrastructure`
- Use cases são o único ponto de entrada para operações de negócio
- Bounded contexts se comunicam via EventBus — nunca por importação direta entre contextos

---

## SOLID

- **S** — Single Responsibility: cada classe/arquivo tem uma razão para mudar
- **O** — Open/Closed: extensão via composição e novos arquivos, não modificação
- **L** — Liskov: implementações de Protocol respeitam o contrato completamente
- **I** — Interface Segregation: Protocols pequenos e focados, não genéricos
- **D** — Dependency Inversion: depender de `Protocol`, não de implementações concretas

---

## Testes

- Testes obrigatórios para todo código de domínio e todos os use cases
- Um arquivo de teste por use case ou domain service
- Nomenclatura: `test_<entidade>_<cenario>_<resultado_esperado>`
- Zero I/O em testes unitários (sem PostgreSQL, sem Redis, sem HTTP)
- Repository Pattern facilita testes: injetar fake, não mockar banco
- Cobertura mínima: `domain/` 90% | `application/` 80% | `infrastructure/` 60% | `interface/` 70%

---

## Anti-Patterns Proibidos

| Anti-pattern | Alternativa correta |
|---|---|
| God Object | Dividir em classes com responsabilidade única |
| Router com lógica de negócio | Router delega imediatamente ao use case |
| Service cruzando bounded contexts diretamente | EventBus ou Application Service dedicado |
| ORM model importado no domínio | Entidade de domínio separada do ORM model |
| FastAPI / SQLAlchemy / Redis importado no domínio | Protocol + DI |
| Prompt hardcoded em service ou router | `src/prompts/` + PromptEngine |
| `os.environ` acessado diretamente | Apenas via `config/settings.py` |
| `utils.py` / `helpers.py` genéricos | Módulo nomeado pela responsabilidade real |
| Arquivo com 400+ linhas acumulando lógica | Dividir por tipo de conceito |
| `schemas.py` com requests e responses juntos | `requests.py` e `responses.py` separados |
| `repositories.py` como nome de interface | `contracts.py` — comunica que é abstração |

---

## Objetivo Final

O projeto deve ser percebido como:

- **Enterprise** — estrutura reconhecível que escala com time e features
- **Altamente manutenível** — qualquer módulo pode ser alterado sem cascata em outros
- **Altamente testável** — domínio e use cases testáveis sem Docker ou serviços externos
- **Escalável** — adicionar um bounded context é reproduzir um padrão existente
- **Fácil para IA navegar** — nomes claros, responsabilidades óbvias, arquivos pequenos e coesos
- **Fácil para humanos** — qualquer desenvolvedor encontra o que precisa em ≤ 10 segundos pelo nome do arquivo
