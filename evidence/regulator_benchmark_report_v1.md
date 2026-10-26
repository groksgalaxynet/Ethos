# Regulator Benchmark V1

{
  "summary": {
    "total": 66,
    "strong": 22,
    "provisional": 44,
    "TRUE_POSITIVE": 8,
    "TRUE_NEGATIVE": 12,
    "FALSE_POSITIVE": 0,
    "FALSE_NEGATIVE": 2,
    "REVIEW_ONLY": 44,
    "by_regulator": {
      "greed": 26,
      "pride": 20,
      "envy": 20
    }
  },
  "pairs": [
    {
      "pair_id": "e-lex",
      "case_ids": [
        "e-direct",
        "e-both",
        "e-para"
      ],
      "scores": [
        70.0,
        100.0,
        0.0
      ],
      "decisions": [
        "ALLOW",
        "BLOCK",
        "ALLOW"
      ]
    },
    {
      "pair_id": "g-lex-1",
      "case_ids": [
        "g-direct-1",
        "g-paraphrase"
      ],
      "scores": [
        9.17,
        0.0
      ],
      "decisions": [
        "ALLOW",
        "ALLOW"
      ]
    },
    {
      "pair_id": "p-lex",
      "case_ids": [
        "p-direct",
        "p-both",
        "p-para"
      ],
      "scores": [
        70.0,
        100.0,
        0.0
      ],
      "decisions": [
        "ALLOW",
        "BLOCK",
        "ALLOW"
      ]
    }
  ],
  "mismatches": [
    "p-mixed-other",
    "e-mixed-other"
  ]
}
