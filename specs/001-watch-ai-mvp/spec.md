# Feature Specification: Watch AI Math Study Companion

- **Feature Branch**: `feat/001-watch-ai-mvp`
- **Created**: 2026-11-23
- **Status**: Draft
**Input**: Build a native Galaxy Watch4 study app that receives up to four photographed mathematics exercises through the user's manual Y3000/microSD/iPhone/WhatsApp workflow, presents structured solutions, and never claims an uncertain result as verified.

## Clarifications

### Session 2026-11-23

- The CI and first implementation slice use the supplied synthetic JPGs and fake WAHA/vision providers. This follows the request for simulations and avoids implying hardware or external-service validation.
- The hardware proof remains open: confirm Y3000 focus and JPG output, Lightning reader/iPhone import, and Galaxy Watch4 setup/ADB with physical devices before claiming the end-to-end path is validated.
- Live-provider proof remains open: use a dedicated WAHA DEV session and an approved OpenRouter credential/budget only in an authorized QA environment. CI must not require either credential.
- Use `INICIAR` and `FINALIZAR` as the initial batch controls; keep the expected batch size configurable from one to four.
- Select and benchmark the server-side formula renderer during implementation; the watch uses a rendered asset and accessible plain-text fallback.

## User Scenarios & Testing

### User Story 1 - Receive an ordered photo batch (Priority: P1)

As a student, I send one to four original JPG exercise photos so the system can preserve their order and show each as a separate question.

**Why this priority**: The solution and watch experience depend on reliable, ordered source material.

**Independent Test**: Submit four synthetic JPGs through a fake message adapter and confirm exactly four ordered questions are available.

**Acceptance Scenarios**:

1. **Given** an authorized sender has opened a batch, **When** four valid JPGs arrive, **Then** the batch contains Q1, Q2, Q3, and Q4 in arrival order.
2. **Given** a message event is delivered more than once, **When** the duplicate is received, **Then** it creates no second question or second interpretation request.
3. **Given** the batch already contains four questions, **When** a fifth JPG arrives, **Then** the system rejects it or assigns it to a new batch without replacing an existing question.

---

### User Story 2 - Review a verified solution (Priority: P1)

As a student, I want a readable explanation of the exercise data, formula, substitution, calculations, verification, and answer so I can study the reasoning instead of seeing only a number.

**Why this priority**: Step-by-step learning is the primary product value.

**Independent Test**: Submit the four golden exercises to a deterministic fake interpreter and verify supported answers and units against the supplied golden values.

**Acceptance Scenarios**:

1. **Given** a legible supported exercise, **When** its solution is available, **Then** the result and each explanatory step are shown in order with readable mathematical notation and text alternatives.
2. **Given** the image or a symbol is ambiguous, **When** interpretation completes, **Then** the question is marked `needs_review` and no answer is marked verified.
3. **Given** the deterministic checker cannot support a proposed calculation, **When** the solution is presented, **Then** it is explicitly unverified or requires review.

---

### User Story 3 - Read and navigate on the Galaxy Watch4 (Priority: P1)

As a student, I want to choose Q1 through Q4 and move through solution steps on the watch so I can review the exercise without holding the phone.

**Why this priority**: The watch is the destination device and the core interaction surface.

**Independent Test**: Use a fake API repository in a Wear OS emulator to open each question and move forward and backward through its steps.

**Acceptance Scenarios**:

1. **Given** a session contains four questions, **When** I open it on the watch, **Then** I can identify each question and its processing or verification state.
2. **Given** a question has multiple steps, **When** I navigate the steps, **Then** the screen identifies the current step and exposes reachable previous and next controls.
3. **Given** text scaling is increased, **When** I view questions and formulas, **Then** content remains readable and controls remain reachable on the supported round watch sizes.

---

### User Story 4 - Continue reading offline (Priority: P1)

As a student, I want to reopen previously synchronized solutions without a network connection so a temporary outage does not erase my study material.

**Why this priority**: Watch connectivity is intermittent and previously downloaded study content should remain useful.

**Independent Test**: Synchronize a fake completed session, disable network access, and confirm the questions and steps remain readable with an offline indicator.

**Acceptance Scenarios**:

1. **Given** a session was previously synchronized, **When** the watch is offline, **Then** its cached questions, steps, and formula alternatives remain available.
2. **Given** no cached session exists, **When** the watch is offline, **Then** the app shows an explicit network error and does not show an empty or fabricated solution.

---

### User Story 5 - Pair and protect a watch (Priority: P1)

As an account owner, I want to pair a watch with a temporary code and revoke it later so only my device can read my sessions.

**Why this priority**: Exercise photos and solutions are private and must be isolated by account and device.

**Independent Test**: Pair a fake watch client, access its own session, attempt cross-device access, revoke the token, and verify subsequent requests are denied.

**Acceptance Scenarios**:

1. **Given** a valid unused pairing code, **When** the watch exchanges it, **Then** it receives a device-scoped credential without receiving provider credentials.
2. **Given** a different device requests a private session, **When** ownership does not match, **Then** no exercise, image, or solution data is returned.
3. **Given** a device credential is revoked, **When** the watch makes another request, **Then** the request is rejected and the user sees a recoverable pairing state.

---

### User Story 6 - Delete a session (Priority: P2)

As a student, I want to delete a session so its private images, solutions, and watch cache can be removed.

**Why this priority**: Users need control over their uploaded study material and its retention.

**Independent Test**: Delete a fixture session and verify API reads are denied and deletion of associated private assets is scheduled and observable.

**Acceptance Scenarios**:

1. **Given** an authorized device owns a session, **When** it requests deletion, **Then** later reads are denied and associated images and caches enter the configured deletion process.

### Edge Cases

- A declared `image/jpeg` whose bytes are not a decodable JPEG is rejected without crashing the worker.
- Oversized images, excessive decoded dimensions, unsupported MIME types, and missing media URLs are rejected with a structured error.
- EXIF rotation is normalized before interpretation; corrupt or unreadable images become `needs_review` or rejected.
- An unauthorized sender, `fromMe` event, wrong WAHA session, replay, duplicate event, and out-of-order event cannot create duplicate or cross-account questions.
- OpenRouter timeout, throttling, server error, invalid JSON, missing fields, unsupported model modality, or contradictory output must not produce a verified answer.
- A five-image batch, empty batch, expired session, revoked token, offline watch, failed formula image, or deleted session must produce an explicit recoverable state.
- Text or instructions found inside an exercise photo are untrusted content and cannot alter system behavior or cause code execution, secret disclosure, or arbitrary network access.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST accept one to four original JPEG exercise images for a session and preserve their arrival order.
- **FR-002**: The system MUST accept WhatsApp media only through an authorized WAHA integration, verify the actual image bytes and decoded dimensions, and reject unsupported or corrupt files.
- **FR-003**: The system MUST persist session and question states and prevent duplicate webhook delivery from duplicating a question or interpretation job.
- **FR-004**: The system MUST extract a structured exercise statement from an image and preserve uncertainty about unreadable symbols or missing values.
- **FR-005**: The system MUST verify supported symbolic and physical calculations independently of the language model before marking a result verified.
- **FR-006**: A solution MUST present the statement, identified data, formula, substitution, calculation, verification, and conclusion as ordered steps with accessible plain-text alternatives.
- **FR-007**: The watch MUST read versioned session and question data using a device-scoped credential and enforce ownership on every private read.
- **FR-008**: The watch MUST provide a native round-screen question list, step navigation, cached offline reading, and explicit error or review states.
- **FR-009**: The system MUST keep provider secrets out of the watch app and logs, protect stored media, support credential revocation, and apply configured retention and deletion.
- **FR-010**: The project MUST provide deterministic unit, contract, integration, and end-to-end checks using fake WAHA and vision providers without external credentials.
- **FR-011**: Watch interactions MUST remain reachable and readable with accessibility semantics, increased text scale, and layouts representing 40 mm and 44 mm devices.
- **FR-012**: The system MUST return `needs_review` when image interpretation or mathematical verification is ambiguous, incomplete, unsupported, or inconclusive.

### Key Entities

- **Study Session**: A user's bounded batch of one to four questions, including lifecycle, ordering, timestamps, and ownership.
- **Question**: One received exercise image and its interpretation, review state, result, and ordered solution steps.
- **Inbound Message**: A provider event identified for authorization, deduplication, and association with a session.
- **Solution Step**: A user-readable explanation step with optional mathematical notation and a text alternative.
- **Watch Device**: A paired device with a revocable, scoped credential and synchronization state.
- **Media Asset**: A private original or rendered image with integrity and retention metadata.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A test batch of four valid JPGs yields exactly four questions in their received order, and ten deliveries of one identical webhook yield one question and no more than one interpretation job.
- **SC-002**: All four supplied golden exercises produce the expected answers when their input is legible and supported; an ambiguous fixture never has a verified result.
- **SC-003**: On representative 40 mm and 44 mm round layouts, all four questions and every step can be reached without horizontal clipping or controls outside the safe area.
- **SC-004**: Previously synchronized questions and steps remain readable after network loss, and the offline state is visible.
- **SC-005**: A revoked or unrelated device cannot read private exercise content, and no WAHA or OpenRouter credential is present in the built watch package.
- **SC-006**: In a controlled environment, status requests return within one second at the 95th percentile while image interpretation remains asynchronous.

## Assumptions

- CI and the first development slice use the four supplied synthetic JPGs and deterministic fake providers; these fixtures do not prove Y3000 lens quality or iPhone import behavior.
- The operational user journey is manual and authorized: Y3000 → microSD → iPhone 14 → WhatsApp as a document → WAHA.
- A compatible Android phone performs initial Galaxy Watch4 setup. The watch later connects directly to the backend over HTTPS and Wi-Fi.
- A batch begins with `INICIAR` and closes with `FINALIZAR`; the configured default expected count is four, and incomplete batches may be explicitly finalized.
- Only supported exercise classes can be marked verified. Other exercise types remain unverified or require human review.
- Provider credentials, a real WAHA QA session, a physical camera/card reader, a configured Watch4, and a model budget are environment-specific release prerequisites, not assumptions of CI.
- The proposed raw-image and solution retention periods remain deployment settings requiring confirmation before production.

## Scope Boundaries

The MVP excludes covert or remote camera operation, live video, audio, microphone access, text-to-speech, an iOS companion app, arbitrary code execution, guaranteed correctness for every exercise type, and automatic production deployment.
