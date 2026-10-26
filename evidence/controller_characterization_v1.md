# Controller Characterization V1

Research-only projection of selected benchmark fixtures.

- g-none: gate=ALLOW; primary=none; secondary=none; temporal=UNSUPPORTED
- g-combo: gate=BLOCK; primary=REGULATOR.GREED.RHI; secondary=none; temporal=UNSUPPORTED
- p-both: gate=BLOCK; primary=REGULATOR.PRIDE.SSN; secondary=REGULATOR.PRIDE.OVERALL; temporal=UNSUPPORTED
- e-both: gate=BLOCK; primary=REGULATOR.ENVY.SOCIAL_COMPARISON; secondary=REGULATOR.ENVY.OVERALL; temporal=UNSUPPORTED
- p-mixed-other: gate=ALLOW; primary=none; secondary=none; temporal=UNSUPPORTED
- g-quote: gate=ALLOW; primary=none; secondary=none; temporal=UNSUPPORTED
- g-key: gate=ALLOW; primary=none; secondary=none; temporal=UNSUPPORTED
- controller-composed-multi-violation: gate=BLOCK; primary=REGULATOR.GREED.HI; secondary=REGULATOR.PRIDE.SSN, REGULATOR.PRIDE.OVERALL; temporal=UNSUPPORTED
- controller-bootstrap: gate=BLOCK; primary=none; secondary=none; temporal=UNSUPPORTED
