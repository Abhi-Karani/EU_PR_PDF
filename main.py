from service.extractor.eu_extractor.eu_extractor import extract_records
from pdf_plumber.full_pipe_plumber import process_pdf
import json



filename = "20250395"
pdf_path = f"PDF/{filename}.pdf"

# json_output = process_pdf(pdf_path)

# with open(f"pdf_plumber/Results/{filename}_reverse.json", "w") as file:
#     json.dump(json_output, file, ensure_ascii=False, indent=4)

print("started")
with open(f"pdf_plumber/Results/{filename}_reverse.json", "r") as file:
    a = json.load(file)
    

content, context = extract_records(a)
with open(f"context_extractor/{filename}_input.txt", "w") as file:
        json.dump({"input":str(content)}, file, ensure_ascii=False, indent=4)

with open(f"context_extractor/{filename}_output.json", "w") as file:
        json.dump(context, file, ensure_ascii=False, indent=4)