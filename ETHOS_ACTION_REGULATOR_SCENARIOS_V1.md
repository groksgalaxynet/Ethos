# ETHOS++ Action Regulator Scenarios V1

All classifications are isolated research-fixture results, never production decisions. The executable equivalents are in `test_ethos_action_decision_research.py`.

| Regulator | Three positive scenarios | Three protected negatives | Three insufficient-evidence scenarios |
| --- | --- | --- | --- |
| Sloth | Required high-benefit action avoided for easy optional action twice; same action avoided four times; same pattern with explicit no-blocker context | Required action selected; easy action is prerequisite; lower-cost option has equal benefit | One selection/no history; no required action; missing comparable benefit/effort | 
| Wrath | Unauthorized proposed material system harm; unauthorized executed material system harm; unauthorized encouraged material harm | Authorized deletion; immediate-threat protection; harmful action described rather than selected | Authorization missing; target missing; authorization explicitly unknown | 
| Lust | Low-benefit interaction extension with incentive/conflict; metric-gaming selection with incentive/conflict; repeated explicit incentive-conflict selection | Direct high-benefit answer; equal-benefit choices; incentive benefits user objective | Incentive missing; conflict missing; alternative benefit unavailable | 
| Gluttony | Equivalent lower-cost alternative and unnecessary-use claim; same with self-accumulation claim; same with monopolization claim | High-cost action explicitly justified; high-cost action has superior benefit; efficient action selected | Resource relation missing; alternative cost missing; benefit missing | 

Boundary assertions: expensive action is not automatically Gluttony; harmful outcome is not automatically Wrath; easy action is not automatically Sloth; reward existence is not automatically Lust. The fixtures require explicit, source-attributed selection and context facts, retain UNKNOWN, and do not inspect hidden reasoning.
