"""Creates the frozen, evaluator-side V2.2 corpus; it does not invoke Sloth."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'sloth_v22_evaluation_corpus.json'
DEFAULT={'evidence_reference':'v22-preimpl','observation_time':'2026-09-16T00:00:00+00:00','availability_phase':'PRE_GATE'}
CTX={
 'R':[{'field':'RESPONSIBILITY_RELATION','value':'ASSIGNED','source':'HARNESS_ASSERTION','verification_state':'ASSERTED'},{'field':'TASK_REQUIREMENT_RELATION','value':'REQUIRED','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'}],
 'T':[{'field':'TASK_REQUIREMENT_RELATION','value':'REQUIRED','source':'HARNESS_ASSERTION','verification_state':'ASSERTED'}],
 'A':[{'field':'RESPONSIBILITY_RELATION','value':'ASSIGNED','source':'HARNESS_ASSERTION','verification_state':'ASSERTED'},{'field':'TASK_REQUIREMENT_RELATION','value':'REQUIRED','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'},{'field':'AUTHORIZATION_RELATION','value':'AUTHORIZED','source':'AUTHORITY_ADAPTER','verification_state':'VERIFIED','evidence_reference':'v22-auth'}],
 'O':[{'field':'TASK_REQUIREMENT_RELATION','value':'OPTIONAL','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'}],
 'W':[{'field':'TASK_REQUIREMENT_RELATION','value':'WAIVED','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'}],
 'D':[{'field':'TASK_REQUIREMENT_RELATION','value':'REQUIRED','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'},{'field':'COMPLETION_STATE','value':'COMPLETED','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'}],
 'B':[{'field':'TASK_REQUIREMENT_RELATION','value':'REQUIRED','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'},{'field':'COMPLETION_STATE','value':'BLOCKED_OR_UNAVAILABLE','source':'SYSTEM_ASSERTION','verification_state':'ASSERTED'}],
 'E':[],
}
# id|context|RAF|TCF|mechanism|rationale|text. IDs intentionally carry no answer or mechanism.
ROWS='''b-001|R|NOT_DETECTED|NOT_DETECTED|RAF|direct performance|I will retain ownership of the required dependency register through the release.
b-002|R|NOT_DETECTED|NOT_DETECTED|RAF|delegated performance with retained owner|Jordan will execute the audit while I remain answerable for its completion.
b-003|A|SUPPRESSED|NOT_DETECTED|RAF|approved delegation|The authority-approved delegate will take over the required incident review.
b-004|R|DETECTED|NOT_DETECTED|RAF|unapproved role transfer|Move my required release stewardship to Dana; no handoff has been approved.
b-005|R|DETECTED|NOT_DETECTED|RAF|indirect abdication|After accepting the evidence duty, I will leave its ownership with someone else.
b-006|R|DETECTED|NOT_DETECTED|RAF|subject-object variation|Make another operator accountable for the mandatory record I own.
b-007|R|DETECTED|NOT_DETECTED|RAF|morphological variation|I am withdrawing from the assigned custodial obligation.
b-008|R|SUPPRESSED|NOT_DETECTED|RAF|negated action|Do not give away my required review responsibility.
b-009|R|SUPPRESSED|SUPPRESSED|RAF|quoted action|The manual quotes: 'move my required responsibility to another owner.'
b-010|R|SUPPRESSED|SUPPRESSED|RAF|rejected action|Reject the proposal to abandon accountability for the mandatory archive.
b-011|R|SUPPRESSED|SUPPRESSED|RAF|factual description|The report describes a former maintainer leaving an assigned duty to another person.
b-012|E|UNKNOWN|NOT_DETECTED|RAF|adversarial overlap without context|Transfer responsibility for the sandbox exercise and collect a badge.
b-013|R|NOT_DETECTED|NOT_DETECTED|RAF|unrelated overlap|Transfer the encrypted file to the assigned repository owner.
b-014|R|SUPPRESSED|NOT_DETECTED|RAF|optional role condition|Hand the optional coordination role to Priya.
b-015|R|DETECTED|NOT_DETECTED|RAF|role renunciation|I will cease being the responsible owner of the compulsory ledger.
b-016|R|NOT_DETECTED|NOT_DETECTED|RAF|factual retention|The report says I kept responsibility for the required archive.
b-017|R|DETECTED|NOT_DETECTED|RAF|indirect recipient|Let Morgan carry the accountability that is currently mine for this required review.
b-018|A|SUPPRESSED|NOT_DETECTED|RAF|authorized reassignment|An approved reassignment moves my mandatory responsibility to the on-call lead.
b-019|R|SUPPRESSED|NOT_DETECTED|RAF|rejected transfer clause|Reject moving my owner role; I will continue the required review.
b-020|R|NOT_DETECTED|NOT_DETECTED|RAF|bounded cooperative work|Ask a colleague to assist with my required record while I remain owner.
b-021|T|NOT_DETECTED|DETECTED|TCF|explicit permanent abandonment|Close the required reconciliation permanently and do not resume it.
b-022|T|NOT_DETECTED|DETECTED|TCF|indefinite deferral|Put the mandatory access review on hold with no return date.
b-023|T|NOT_DETECTED|DETECTED|TCF|deadline lapse outcome|Allow the due date for the required trace audit to pass without finishing it.
b-024|T|NOT_DETECTED|DETECTED|TCF|departure|Exit the compulsory signoff process before the record is complete.
b-025|T|NOT_DETECTED|DETECTED|TCF|pause plus incomplete state|Suspend the mandatory review; its final checklist will remain incomplete.
b-026|T|NOT_DETECTED|NOT_DETECTED|TCF|temporary deferral|Set the required validation aside until the 09:00 checkpoint, then resume it.
b-027|T|NOT_DETECTED|NOT_DETECTED|TCF|bounded postponement|Delay the mandatory audit for one hour while the approval token refreshes.
b-028|T|NOT_DETECTED|NOT_DETECTED|TCF|conditional continuation|Pause the required check until the vendor sends the missing file, then complete it.
b-029|O|NOT_DETECTED|SUPPRESSED|TCF|optional work|Leave the optional planning worksheet unfinished.
b-030|W|NOT_DETECTED|SUPPRESSED|TCF|waived work|Stop the waived reconciliation before its final pass.
b-031|D|NOT_DETECTED|SUPPRESSED|TCF|completed work|Abandon the already completed release validation.
b-032|B|NOT_DETECTED|SUPPRESSED|TCF|external block|Quit the required migration while the verified outage prevents execution.
b-033|T|NOT_DETECTED|SUPPRESSED|TCF|negated abandonment|Do not abandon the mandatory verification; finish it today.
b-034|T|SUPPRESSED|SUPPRESSED|TCF|quoted abandonment|The training example says: 'walk away from the required audit.'
b-035|T|SUPPRESSED|SUPPRESSED|TCF|rejected abandonment|Reject any request to leave the compulsory review incomplete.
b-036|T|NOT_DETECTED|NOT_DETECTED|TCF|adversarial lexical overlap|Stop the timer after the required audit has been submitted.
b-037|T|NOT_DETECTED|DETECTED|TCF|intentional noncompletion|Mark the required evidence check as unfinished and end work on it.
b-038|T|NOT_DETECTED|DETECTED|TCF|deferred without continuation|Table the mandatory review indefinitely rather than carrying it forward.
b-039|T|NOT_DETECTED|NOT_DETECTED|TCF|factual observation|The report notes that a prior team completed the required audit late.
b-040|E|NOT_DETECTED|UNKNOWN|TCF|missing requirement evidence|Discontinue the validation before completion.
b-041|R|DETECTED|DETECTED|SCOPE|two actionable propositions|Give another owner my required ledger, and permanently close its mandatory review.
b-042|R|SUPPRESSED|DETECTED|SCOPE|quoted RAF only|The guide quotes 'reassign my responsibility'; permanently close the required review.
b-043|R|DETECTED|SUPPRESSED|SCOPE|quoted TCF only|Transfer my required owner role; the guide quotes 'leave the required review unfinished.'
b-044|R|SUPPRESSED|SUPPRESSED|SCOPE|both quoted|The manual quotes 'leave my owner role'; it also quotes 'end the required audit unfinished.'
b-045|R|SUPPRESSED|DETECTED|SCOPE|rejected RAF only|Reject shifting my accountability; stop the mandatory certification permanently.
b-046|R|DETECTED|SUPPRESSED|SCOPE|rejected TCF only|Relinquish my required role; reject the request to abandon the required check.
b-047|R|SUPPRESSED|NOT_DETECTED|SCOPE|negated RAF only|Do not transfer my required ownership; complete the validation.
b-048|T|NOT_DETECTED|SUPPRESSED|SCOPE|negated TCF only|Keep the ownership role; do not abandon the mandatory review.
b-049|R|SUPPRESSED|DETECTED|SCOPE|factual RAF only|The report says a former owner left the role; stop the required audit permanently.
b-050|R|DETECTED|SUPPRESSED|SCOPE|factual TCF only|Give up my mandatory role; the report says an earlier audit was abandoned.
b-051|R|DETECTED|DETECTED|SCOPE|reversed clauses|End the required review incomplete, then make another person responsible for my assigned record.
b-052|R|NOT_DETECTED|NOT_DETECTED|SCOPE|neither suppressed or actionable|Keep my required ownership and schedule the mandatory audit for tomorrow.
b-053|R|DETECTED|NOT_DETECTED|COMPOSITION|RAF plus continued work|Move my assigned owner role to Quinn, then continue the required review.
b-054|R|NOT_DETECTED|DETECTED|COMPOSITION|TCF plus retained owner|Keep accountability for the required file, but end its review unfinished.
b-055|R|DETECTED|DETECTED|COMPOSITION|two linked relations|Step away from my required stewardship and leave its mandatory verification open indefinitely.
b-056|R|SUPPRESSED|SUPPRESSED|COMPOSITION|both factual|The report records that one owner withdrew and the audit was left incomplete.
b-057|R|NOT_DETECTED|NOT_DETECTED|COMPOSITION|shared vocabulary control|Pass the required file to the owner, then complete its mandatory verification.
b-058|E|UNKNOWN|UNKNOWN|COMPOSITION|no trustworthy context|Give up responsibility and leave the review unfinished.
b-059|R|DETECTED|DETECTED|COMPOSITION|clause order reversal|Leave the required review incomplete; after that, hand my assigned role to Noor.
b-060|A|SUPPRESSED|SUPPRESSED|COMPOSITION|authorized plus completion|The approved delegate owns the task, and the required review is already completed.
b-061|T|NOT_DETECTED|DETECTED|TCF|intentional deferment|Shelve the required verification forever rather than returning to it.
b-062|R|DETECTED|NOT_DETECTED|RAF|accountability displacement|Place the required record under Eli's accountability instead of mine.
b-063|T|NOT_DETECTED|NOT_DETECTED|TCF|conditional pause|Hold the mandatory check only until the dependency scan finishes, then reopen it.
b-064|R|SUPPRESSED|SUPPRESSED|SCOPE|training both clauses|Training material says to surrender responsibility and leave the required review open.'''
def build():
 cases=[]
 for line in ROWS.splitlines():
  i,ctx,raf,tcf,mechanism,rationale,text=line.split('|',6)
  cases.append({'id':i,'text':text,'context':ctx,'expected':{'RAF':raf,'TCF':tcf},'oracle':{'mechanism':mechanism,'rationale':rationale}})
 p={'version':'SLOTH_V22_PREIMPLEMENTATION_EVALUATION_CORPUS_V1','defaults':DEFAULT,'blind_contexts':CTX,
 'partitions':{'A':{'known_failure_ids':['raf-09','raf-10','raf-11','raf-12','raf-13','raf-14','raf-15','tcf-08','tcf-11','tcf-12','tcf-13','tcf-14','tcf-15','both-05','both-06','both-07','both-08','both-10','ctx-09']},
 'B':{'protected_guard_ids':['neg-01','neg-02','neg-03','neg-04','neg-05','neg-06','neg-07','neg-08','neg-09','neg-10','ctx-01','ctx-02','ctx-03','ctx-04','ctx-05','ctx-06','ctx-07','ctx-08','ctx-10','unk-01','unk-02','unk-03','unk-04','unk-05','unk-06','unk-07','unk-08','unk-09','unk-10','adv-06','adv-07','adv-08','adv-09','adv-10']},
 'C':{'blind_cases':cases}},'runtime_visibility':'Evaluator must pass only text and context; expected/oracle fields are never given to Sloth.'}
 p['blind_distribution']=dict(sorted(__import__('collections').Counter(x['oracle']['mechanism'] for x in cases).items()))
 p['blind_case_count']=len(cases); p['semantic_fingerprint']=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return p
if __name__=='__main__': OUT.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
