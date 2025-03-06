Process PDFs for EU_PR:
  1. Extract PDF content retaining structure (text -> table -> text and so on) (done)
  2. That becomes input to the Context_call. This gives context corresponding to each table and person/entity (if mentioned individually as paragraph)
  3. We pass each row with the corresponding table's context and non tabular data with its corresponding context to the data-point-extractor call
  4. We extract all the information along with the change type in the data-point-extractor call
