Process PDFs for EU_PR:
  1. Set up two pipeline, get Context by extracting PDF structure (text -> table -> text and so on)
  2. feed the context along with each row to the LLM
  3. get LLM output
