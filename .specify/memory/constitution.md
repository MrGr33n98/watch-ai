# Watch AI Constitution

## Core Principles

### I. Correctness Before Confidence

Mark a solution `verified` only when a deterministic verifier supports the problem class and checks the result. Use `needs_review` when image interpretation is ambiguous, inputs are missing, or verification is inconclusive. Never invent unreadable values or claim verification based on a model response alone.

### II. Test First (TDD)

For each implementable task, write the deterministic test first, run it and record a legitimate RED result, implement the smallest change that makes it pass, then refactor and rerun the relevant checks. Do not remove or skip a critical test to make CI green. Coverage does not replace execution evidence.

### III. Domain-Driven Design

Keep the domain independent of FastAPI, SQLAlchemy, WAHA, OpenRouter, and Android UI frameworks. Separate ingestion, sessions, interpretation, math verification, presentation, and watch delivery into bounded contexts with replaceable adapters. Keep mathematical rules out of presentation code.

### IV. API-First Contracts

Define and validate OpenAPI contracts for every backend capability consumed by the watch or an integration. Use typed responses, structured errors, explicit authorization, and compatibility checks. Contract changes require a documented reason and updated tests.

### V. Privacy and Security by Default

Keep WAHA and OpenRouter credentials on the server. Validate image bytes, MIME, size, and decoded dimensions; store originals privately; authorize every session read by device ownership; make webhook ingestion idempotent; and enforce configured retention and deletion. Do not execute OCR or model output as code or as a network destination.

### VI. Native Wear OS Experience

Build the watch UI with Kotlin and Jetpack Compose for Wear OS Material 3. Design for circular displays, readable scaled text, accessible controls, and offline access to cached solutions. Do not request microphone access or implement speech input, audio, or text-to-speech.

### VII. Reproducibility and Observability

Pin dependencies and toolchains, keep fake-based CI independent of private services, and record sanitized test, build, performance, and security evidence. Never describe a mock, skipped test, or unavailable device check as a real integration pass.

### VIII. No Silent Deployment

The agent may inspect, implement, and validate changes on an isolated feature branch. It must not merge, publish secrets, change production WAHA/Avalia Solar infrastructure, or deploy without explicit approval. A draft pull request may be prepared for review.

## Additional Constraints

- The intended path is manual capture and transfer: Y3000 JPG → microSD → iPhone 14 → WhatsApp → WAHA → API → Galaxy Watch4. Do not add covert capture, remote camera control, live video, or an iPhone companion app.
- Use FastAPI/Python, PostgreSQL, OpenRouter multimodal models, WAHA webhooks, SymPy, and Pint behind domain ports. Use Docker Compose and GitHub Actions for reproducible local and CI workflows.
- Limit a session to four ordered questions. A fifth image must be rejected or assigned to a separate session; it must never overwrite an existing question.
- Default image admission limits are 8 MiB and 24 megapixels, configurable by deployment. Enforce actual JPEG decoding and pixel limits, not just the filename or declared MIME type.
- Keep original images in private storage. Use the proposed 24-hour image and 30-day solution retention defaults only after they are exposed as configuration and documented for the deployment.
- The Galaxy Watch4 requires initial setup with a compatible Android phone. It communicates with the backend directly over HTTPS/Wi-Fi and does not use iPhone pairing or the Android Wearable Data Layer as an iPhone bridge.

## Development Workflow

- Follow Constitution → Specify → Clarify → Plan → Tasks → Analyze → Implement. Keep the source requirements and generated feature artifacts aligned.
- Implement in dependency order and vertical slices. Each task records RED, GREEN, REFACTOR, risks, files, and actual evidence; keep unresolved hardware or credential-dependent work pending rather than marking it complete.
- Run unit, contract, integration, E2E, security, accessibility, and build checks appropriate to the slice. CI uses synthetic JPGs and fakes; real WAHA/OpenRouter and physical-device checks are isolated manual QA gates.
- Keep the debug APK free of provider secrets. Store watch credentials in Android Keystore, support revocation, and require TLS for production traffic.
- Do not merge or deploy automatically. Prepare review artifacts and identify any remaining gates honestly.

## Governance

This constitution governs implementation plans, tasks, code review, and release evidence. Amendments require a documented rationale, a semantic version change, and review of affected specifications, contracts, tests, and security controls. Version changes use MAJOR for incompatible governance changes, MINOR for new or materially expanded principles, and PATCH for non-semantic clarification. Every feature review must check compliance with these principles. Quality gates are defined in the feature specification and test strategy; unresolved P0 correctness or security failures block release.

**Version**: 1.0.0 | **Ratified**: 2026-11-23 | **Last Amended**: 2026-11-23
