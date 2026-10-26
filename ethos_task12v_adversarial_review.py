"""Deterministic, read-only adversarial review of frozen Task 12U V1 design."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from pathlib import Path
R=Path(__file__).parent
def h(n):return hashlib.sha256((R/n).read_bytes()).hexdigest()
def main():
 attacks=[
 ('A01','ethical predicate in relation type','semantic neutrality','PASS_WITH_CLARIFICATION','MODERATE','versioned bounded relation vocabulary rejects it; V1 must enumerate the validator-owned vocabulary before implementation.'),
 ('A02','ethical predicate via state/outcome/metadata/extension','unbounded semantic escape','FAIL_REQUIRES_REVISION','CRITICAL','V1 says bounded states but does not explicitly define opaque metadata as non-consumable or close all state/outcome extension channels.'),
 ('A03','assertor/actor cross-agent reversal','assertor != actor','PASS','MINOR','assertion envelope and relation role bindings remain separate.'),
 ('A04','role title becomes identity/authority','identity != role != authority','PASS_WITH_CLARIFICATION','MODERATE','design separates them, but needs a normative validation rule that role labels cannot populate authority decisions.'),
 ('A05','self-certified completion','assertion != verification','PASS','MINOR','agent declaration remains declaration; fact-specific verification required.'),
 ('A06','self-certified authorization','authority fact-specific','PASS','MINOR','declared authorization cannot replace authenticated authorizer evidence.'),
 ('A07','cross-agent false claim','assertor/subject separation','PASS','MINOR','claim retains A assertor and B subject; no verification collapse.'),
 ('A08','conflicting claims overwrite','conflict != resolution','PASS_WITH_CLARIFICATION','MODERATE','immutable competing assertions are required, but contradiction-link lifecycle/current-state derivation needs a precise review rule.'),
 ('A09','swarm echo counted as independent','repetition != independence','PASS_WITH_CLARIFICATION','MODERATE','lineage and independence UNKNOWN are present; producer requirements for copied-claim parent lineage need specification.'),
 ('A10','independent colluding claims become consensus','agreement != authority','PASS','MINOR','V1 records observations but makes no consensus truth decision.'),
 ('A11','claimed identity spoofs authenticated source','claimed != authenticated identity','PASS_WITH_CLARIFICATION','MODERATE','boundary is stated, but authentication-status reference/absence semantics need normative definition.'),
 ('A12','scope collision agent_2 across swarms','scoped identity','PASS_WITH_CLARIFICATION','MODERATE','scope/namespace is required but canonical scope composition is not specified.'),
 ('A13','delegation chain infers authority/responsibility','no transitive ethical inference','PASS','MINOR','requested/performed/authorized relations stay separate.'),
 ('A14','joint action selects primary/equal responsibility','many-to-many participation','PASS','MINOR','relation-based participation supports all actors without responsibility inference.'),
 ('A15','stop(timer) becomes stop(task)','target binding/UNKNOWN','PASS_WITH_CLARIFICATION','MAJOR','V1 represents typed targets and UNKNOWN, but target type/cardinality conformance needs explicit validator rules.'),
 ('A16','event ID used as task ID','typed relation integrity','FAIL_REQUIRES_REVISION','MAJOR','design calls entities typed but does not define relation endpoint-type constraints or invalid-reference behavior.'),
 ('A17','post-action fact used pre-action','temporal availability','PASS_WITH_CLARIFICATION','MAJOR','availability phases are required; consumer enforcement and phase ordering need normative acceptance rules.'),
 ('A18','late observation of earlier event rewrites knowledge','event time != availability time','PASS','MINOR','both times and availability phase are distinct.'),
 ('A19','retroactive authorization','validity/availability','PASS_WITH_CLARIFICATION','MAJOR','authorization relation includes time/validity conceptually but exact pre-action rule needs specification.'),
 ('A20','state transition overwrites prior state','immutable state history','PASS','MINOR','immutable records plus supersession links preserve both states.'),
 ('A21','deadline turns into deadline violation','neutral deadline fact','PASS','MINOR','deadline/outcome are neutral; violation is prohibited.'),
 ('A22','derived low-authority claims gain authority','derived != observed','PASS_WITH_CLARIFICATION','MAJOR','lineage/non-upgrade invariant exists but authority propagation algorithm is not specified.'),
 ('A23','derived ancestry becomes irrecoverable','derivation lineage','PASS','MINOR','parent IDs/rule/version preserve reference chain.'),
 ('A24','regulator output re-enters as independent evidence','circularity','PASS_WITH_CLARIFICATION','MAJOR','origin/regulator-output marker is required but its mandatory propagation needs definition.'),
 ('A25','NLP interpretation labeled observed','interpreted != observed','PASS','MINOR','origin kind explicitly separates INTERPRETED.'),
 ('A26','UNKNOWN coerced to default entity/state','missing != false','PASS','MINOR','UNKNOWN is first class at relation role/state/authority levels.'),
 ('A27','producer self-grants authority','authority policy separation','FAIL_REQUIRES_REVISION','CRITICAL','Authority is declared outside data, but V1 lacks an explicit prohibition/quarantine rule for payload authority/trust/priority fields and a policy-decision reference boundary.'),
 ('A28','assertor self-appoints verifier','verification independence','PASS_WITH_CLARIFICATION','MODERATE','assertor/verifier identities survive; independence remains UNKNOWN but policy must receive that relation.'),
 ('A29','unbounded metadata becomes consumable structure','metadata boundary','FAIL_REQUIRES_REVISION','CRITICAL','V1 lacks a mandatory opaque-metadata/non-consumability partition; extensions could recreate a semantic graph.'),
 ('A30','unknown relation vocabulary version maps silently','versioning','PASS_WITH_CLARIFICATION','MAJOR','versions are required; unsupported version must be normatively rejected/quarantined, not only described.'),
 ('A31','malformed relation/reference/lineage','deterministic validation','FAIL_REQUIRES_REVISION','MAJOR','V1 lacks an explicit conformance disposition table for bad IDs, endpoint types, cycles, parents, phases, and verifier identity.'),
 ('A32','existing regulators accidentally consume V1','current isolation','PASS_WITH_CLARIFICATION','MODERATE','additive/non-consumption intent is sound; implementation authorization must require explicit import/routing isolation tests.'),
 ('A33','Sloth traceability smuggles abandonment/displacement','regulator isolation','PASS','MINOR','V1 represents prerequisites only; ethical relation is rejected.'),
 ('A34','Wrath action facts require Wrath field','neutrality','PASS','MINOR','generic actor/target/order/outcome/magnitude can remain neutral.'),
 ('A35','N=1 requires swarm semantics','single-agent compatibility','PASS','MINOR','same scoped entity/relation model works with one participant.'),
 ('A36','100-agent distributed evidence breaks identity/lineage','swarm/distributed scaling','PASS_WITH_CLARIFICATION','MODERATE','many-to-many/scoped lineage model scales conceptually; distributed clock, source-instance, transport preservation require design clarification.'),
 ('A37','minimality of dedicated task/event/state concepts','minimality','PASS_WITH_CLARIFICATION','MODERATE','demonstrated cases justify them, but relation vocabulary and state family boundaries need pruning during revision.'),
 ('A38','completeness for 12S requirements','completeness','PASS_WITH_CLARIFICATION','MAJOR','neutral prerequisites are representable if authoritatively supplied; text-only extraction remains deliberately outside V1.')]
 rows=[{'attack_id':a,'description':b,'invariant':c,'result':d,'severity':e,'evidence':f,'v1_handles_now':d=='PASS','clarification_sufficient':d=='PASS_WITH_CLARIFICATION','revision_required':d=='FAIL_REQUIRES_REVISION'} for a,b,c,d,e,f in attacks]
 counts=Counter(x['result'] for x in rows);sev=Counter(x['severity'] for x in rows)
 review={'version':'TASK12V_ADVERSARIAL_REVIEW_V1','specimen_hashes':{n:h(n) for n in ['ETHOS_STRUCTURAL_EVIDENCE_CONTRACT_V1_DESIGN.md','ethos_structural_evidence_contract_v1_design.json','ethos_task12u_contract_traceability.json','ethos_task12u_contract_abuse_review.json','ethos_task12t_structural_provenance_authority.json','sloth_task12s_input_contract_audit.json','sloth_contextual_measurement_v21_research.py']},'frozen_specimen':'Task12U V1 was not modified.','attack_metrics':dict(counts),'severity_metrics':dict(sev),'required_revisions':[x for x in rows if x['revision_required']],'remaining_unknowns':['Exact authority-policy decision reference shape','canonical scope composition','independence evidence producer requirements','distributed clock/transport semantics'],'readiness':'V1 DESIGN REQUIRES REVISION BEFORE IMPLEMENTATION'}
 review['semantic_fingerprint']=hashlib.sha256(json.dumps(review,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 invariants={'version':'TASK12V_INVARIANT_RESULTS_V1','results':{x['invariant']:x['result'] for x in rows},'automatic_revision_conditions_triggered':['unbounded semantic extension/metadata channel','producer self-granted authority boundary unspecified','malformed relation conformance unspecified']}
 (R/'ethos_task12v_structural_contract_adversarial_review.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n');(R/'ethos_task12v_attack_matrix.json').write_text(json.dumps({'version':'TASK12V_ATTACK_MATRIX_V1','attacks':rows},indent=2,sort_keys=True)+'\n');(R/'ethos_task12v_invariant_results.json').write_text(json.dumps(invariants,indent=2,sort_keys=True)+'\n')
 (R/'ETHOS_TASK12V_STRUCTURAL_CONTRACT_ADVERSARIAL_REVIEW.md').write_text(f'''# Structural Evidence Contract V1 — Adversarial Review

## Disposition

**V1 DESIGN REQUIRES REVISION BEFORE IMPLEMENTATION.** Task 12U remains frozen; no revision was made here.

## Metrics

- Total attacks: {len(rows)}
- PASS: {counts['PASS']}
- PASS_WITH_CLARIFICATION: {counts['PASS_WITH_CLARIFICATION']}
- FAIL_REQUIRES_REVISION: {counts['FAIL_REQUIRES_REVISION']}
- UNKNOWN: {counts['UNKNOWN']}

## Required revisions

1. Close every relation/state/outcome/extension/metadata channel: opaque metadata must be non-consumable, and bounded vocabulary enforcement must be normative.
2. State that producers cannot self-assign authority/trust/priority; authority policy needs a separate decision/reference boundary.
3. Define deterministic conformance dispositions for endpoint types, references, duplicate IDs, invalid phase, derivation parents/cycles, verifier identity, and unsupported versions.

The core provenance model survives: assertions, verification, authority, identities, conflicts, UNKNOWN, multi-actor relations, temporal availability, lineage, and regulator neutrality are conceptually sound. But the three defects above trigger the automatic revision rule because they could permit semantic/authority laundering or nondeterministic malformed evidence handling.
''')
if __name__=='__main__':main()
