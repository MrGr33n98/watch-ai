# ADR 0004: OpenRouter multimodal transport

- Status: Accepted for the adapter contract; live model selection remains gated by T005.
- Date: 2026-11-23

## Decision

Use OpenRouter's Chat Completions endpoint with a multimodal `image_url` content
part containing a JPEG data URL. Keep image bytes private in the API request and
do not ask the model to solve, evaluate, or execute expressions. The adapter asks
for a small typed JSON transcription and marks unclear input for human review.
Server credentials and the model slug are read from `OPENROUTER_API_KEY` and
`OPENROUTER_MODEL`; neither belongs in the Wear OS application.

The adapter uses an explicit timeout, a bounded retry count for timeouts, 429,
and 5xx responses, and validates the returned JSON with a strict typed schema.
No live request is made until the model and spending budget are approved.

## References

- [OpenRouter Chat Completions API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion)
- [OpenRouter image input guide](https://openrouter.ai/blog/tutorials/send-image-to-llm/)
