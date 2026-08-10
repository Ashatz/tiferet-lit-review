# AGENTS.md — Tiferet Literature Review Knowledge Base

## Project Overview

**tiferet-lit-review** is a literature review knowledge base application built
on the [Tiferet](https://github.com/greatstrength/tiferet) framework. It holds
a growing body of research reading — sources, the citations pulled from them,
the themes those citations belong to, and the bibliographic record needed to
cite them correctly — organized around the argument the reader is building,
not around the sources themselves.

This RFP (RFP-1: Foundation) stands up the runnable application skeleton every
later RFP registers into. It contains no domain behavior: no `Source`,
`Citation`, `Theme`, `Linkage`, or `Outline` artifact exists yet.

- **Repository:** https://github.com/Ashatz/tiferet-lit-review
- **Built with:** [Tiferet](https://github.com/greatstrength/tiferet) `>=2.0.0b3`
- **Python:** `>=3.10`

## Layer Overview

The application package (`app/`) follows the Tiferet layer convention. Each
package below is currently empty (only `__init__.py`) except where noted, so
later RFPs add to an existing package rather than creating it.

```
app/
├── assets/       # Constants, exceptions -- also holds the config YAMLs for now
│                 # (app.yml, di.yml, feature.yml, error.yml, cli.yml); configs
│                 # can be stored here until a more permanent location is decided.
├── domain/       # Domain objects (empty -- no domain objects yet)
├── events/       # Domain events -- system.py::Ping is the only event so far
├── interfaces/   # Service ABCs (empty -- no domain services yet)
├── mappers/      # Aggregates + transfer objects (empty)
├── repos/        # Repository implementations (empty)
├── di/           # App-level DI helpers (empty -- wiring lives in the configs)
├── contexts/     # Runtime contexts (empty)
└── blueprints.py # build_app entrypoint, exported as App
```

## Key Concepts

- **DomainObject** — Tiferet's base domain model class, backed by Pydantic v2
  (`pydantic.BaseModel`). Domain objects are read-only; mutation goes through
  Aggregates. See `tiferet.domain.core.DomainObject` in the installed
  package for the authoritative definition.
- **DomainEvent** — the base class for domain operations
  (`tiferet.events.core.DomainEvent`). Entry point is `execute(**kwargs)`.
  This RFP's only event is `app/events/system.py::Ping`.
- **Blueprints** — thin orchestration entrypoints that wire and delegate; see
  `app/blueprints.py::build_app`, exported as `App` from `app/__init__.py`.

## Runtime Flow

```
App('lit_review')                             # app/blueprints.py: build_app()
  └─ tiferet.App(interface_id, app_config=...)  # framework's core build_app
       └─ AppInterfaceContext / AppSessionContext
            └─ FeatureContext.execute_feature()
                 └─ DomainEvent.handle(Ping, ...) -> 'pong'
```

The CLI entrypoint (`lit_review_cli.py`) follows the same path via the
framework's `CLI` blueprint, dispatching `sys.argv` to the `system.ping`
feature. Run it with:

```bash
python lit_review_cli.py system ping
```

## Configuration

- `app/assets/app.yml` — the `lit_review` interface/session declaration,
  including per-domain service overrides pointing at the other four config
  files (and the framework's own `logging_service`, reusing `app.yml` since
  this RFP does not introduce a dedicated logging config).
- `app/assets/di.yml` — service registrations (currently just `ping_event`).
- `app/assets/feature.yml` — feature workflows (currently just `system.ping`).
- `app/assets/error.yml` — the domain error catalog (empty; framework
  defaults are seeded at runtime regardless of file content).
- `app/assets/cli.yml` — CLI command bindings (currently just `system ping`).

## Domain Rationale

This RFP is domain-behavior-free by design. For the rationale behind the
domain this application will eventually implement, see:

- [`docs/domain-vision.md`](docs/domain-vision.md) — why the knowledge base
  organizes by theme rather than by source.
- [`docs/core-domain-distillation.md`](docs/core-domain-distillation.md) — the
  domain's vocabulary, behaviors, and relationships in detail.

## Contributing

This project follows the Tiferet framework's contribution conventions,
including the structured code style (artifact comments, RST docstrings) and
the RFP (Request for Prototype) collaboration stream for exploratory or
architectural work. See the framework's own
[CONTRIBUTING.md](https://github.com/greatstrength/tiferet/blob/main/CONTRIBUTING.md)
for the full workflow reference.
