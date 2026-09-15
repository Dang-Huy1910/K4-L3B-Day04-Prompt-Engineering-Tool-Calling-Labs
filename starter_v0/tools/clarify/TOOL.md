---
name: clarify
track: core
kind: control
requires_env: []
inputs: [question, response_type, options, action, action_args]
outputs: [question, response_type, options, action, action_args, awaiting_user]
side_effect: false
---
# clarify

Returns a question to the user and pauses until the next user turn.
`response_type` is free text, yes/no, or a choice from `options`.
For confirmation of a write action, set `action` to the proposed tool name and
put its exact, unconfirmed payload in `action_args`. These optional fields let
the application bind a later yes/no response to the reviewed payload.
