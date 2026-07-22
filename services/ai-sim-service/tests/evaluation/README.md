# Tutor evaluation tests

Golden-set based checks for the tutor's answer quality and retrieval
relevance (see `ai_sim_service.tutor.evaluation`). Kept separate from
`tests/unit/` and `tests/integration/` because these are non-deterministic by
nature and are evaluated against quality thresholds rather than exact
assertions.
