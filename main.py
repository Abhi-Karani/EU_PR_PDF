from service.extractor.eu_extractor.eu_extractor import extract_records
import json

print("started")
filename = "20232501"
with open(f"pdf_plumber/Results/{filename}_reverse.json", "r") as file:
    a = json.load(file)
    

extract_records(a)