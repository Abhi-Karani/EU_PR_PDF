Process PDFs for EU_PR:
  1. Extract PDF content retaining structure (text -> table -> text and so on)->(done)
*       a. Get bbox_tables for tables on each page
        b. Get text outside the bbox_tables
        c. Get tables inside the bbox_tables
        d. Reverse (RTL scripts) for each paragraph and each cell
  5. This becomes input to the Context_call. ->(inprogress)
*       a. Get context corresponding to each table
        b. Get context corresponding to each person/entity (if mentioned individually as paragraph)
  6. Prep Data:
*       a. Pass each row with the context of the table
        b. Pass non tabular elements (2b) with their corresponding contexts
  7. Extract all the information along with the change type in the data-point-extractor call
