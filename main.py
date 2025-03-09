from service.extractor.eu_extractor.eu_context_extractor import extract_context
from service.extractor.eu_extractor.eu_extractor import extractor
from pdf_plumber.full_pipe_plumber import process_pdf
from service.formater.table_cleaner import clean_json_tables
from service.formater.context_formater import format_context, format_pdf_output_for_context_call
import json



filename = "20242697"
pdf_path = f"PDF/{filename}.pdf"

pdf_plumber_output_reverse = process_pdf(pdf_path)

with open(f"content_store/{filename}/plumber_raw.json", "w") as file:
    json.dump(pdf_plumber_output_reverse, file, ensure_ascii=False, indent=4)

print("-------------------pdf plumber raw extraction complete-----------------")

with open(f"content_store/{filename}/plumber_raw.json", "r") as file:
    pdf_plumber_output_reverse = json.load(file)

pdf_plumber_cleaned_output = clean_json_tables(pdf_plumber_output_reverse)
with open(f"content_store/{filename}/plumber_cleaned.json", "w") as file:
    json.dump(pdf_plumber_cleaned_output, file, ensure_ascii=False, indent=4)
    
print("-------------------pdf plumber raw data cleaning complete-----------------")

with open(f"content_store/{filename}/plumber_cleaned.json", "r") as file:
    pdf_plumber_cleaned_output = json.load(file)

content_for_context_call = format_pdf_output_for_context_call(pdf_plumber_cleaned_output)

with open(f"content_store/{filename}/context_call_input.json", "w") as file:
    json.dump({"input":content_for_context_call}, file, ensure_ascii=False, indent=4)

print("-------------------input for context call ready-----------------")
    
    
with open(f"content_store/{filename}/context_call_input.json", "r") as file:
    temp = json.load(file)
    content_for_context_call = temp.get("input","")

context = extract_context(content_for_context_call)

with open(f"content_store/{filename}/context_call_output.json", "w") as file:
        json.dump(context, file, ensure_ascii=False, indent=4)
        
print("-------------------context call complete-----------------")

with open(f"content_store/{filename}/context_call_output.json", "r") as file:
        context = json.load(file)

content_for_extraction = format_context(context)

with open(f"content_store/{filename}/extractor_input.json", "w") as file:
        json.dump(content_for_extraction, file, ensure_ascii=False, indent=4)
        
print("-------------------input for extractor Ready-----------------")

with open(f"content_store/{filename}/extractor_input.json", "r") as file:
        context = json.load(file)

records = extractor(context)

with open(f"content_store/{filename}/extractor_output.json", "w") as file:
        json.dump(records, file, ensure_ascii=False, indent=4)

print("-------------------extractor complete-----------------")

# if-else less than 5 pages walla
# tokens walla chaiyeh text mein
# if tokens greater than X then seperate flow/handle
# pidantic models