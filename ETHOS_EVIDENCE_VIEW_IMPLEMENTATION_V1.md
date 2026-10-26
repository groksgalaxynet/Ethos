# ETHOS Evidence View Implementation V1

`ethos_evidence_view.py` is an immutable compatibility wrapper over unchanged
`proposal_text_sources()` and `contextual_cue_observations()`. `SourceRecord`,
`CueRecord`, and `EvidenceView` preserve traversal order, source identity/text/
metadata, cue spans, and local contexts. Points, scores, contribution, policy,
and regulator ownership are absent. No factual atoms are emitted yet; action,
temporal, and target facts remain deferred. Canonical serialization and SHA-256
fingerprint identify a snapshot only. Pride remains on its legacy path.

## Decision

EVIDENCE_VIEW_IMPLEMENTATION_VERIFIED
