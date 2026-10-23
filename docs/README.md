# AgriDirect Documentation

This directory contains all project documentation, organised by type.

| Directory | Contents |
|---|---|
| [`srs/`](./srs/) | Software Requirements Specification — functional and non-functional requirements |
| [`dfd/`](./dfd/) | Data Flow Diagrams — system data flows, context diagrams, and process decompositions |
| [`architecture/`](./architecture/) | Architecture Decision Records (ADRs) and system design documents |
| [`database/`](./database/) | Database schema documentation, ERDs, and data dictionary |

---

## Documentation Standards

- **SRS documents** follow a structured format: introduction, actors, use cases, functional requirements, non-functional requirements, constraints.
- **DFDs** are maintained as diagrams (Mermaid, draw.io, or PNG) plus accompanying descriptions. Start with a context diagram (Level 0), then decompose.
- **ADRs** use the format: Title, Status, Context, Decision, Consequences. Stored as numbered files (`ADR-001-*.md`).
- **Database docs** include an ERD plus a data dictionary describing each table, column, type, and constraint.

All documentation must be kept up to date as the implementation evolves. The source of truth for behaviour is always the implementation + tests; documentation explains *why* decisions were made.
