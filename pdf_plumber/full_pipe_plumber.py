import pdfplumber
import json
from bidi.algorithm import get_display


LANDSCAPE_COORDS = (34, 0, 783, 595)
PORTRAIT_COORDS = (0.3, 63.34, 594.7, 807.12)
TABLE_EXPANSION_VERTICAL = 0
TABLE_EXPANSION_HORIZONTAL = 0.3
TABLE_SETTINGS_LINEANT = {"intersection_tolerance":100}
TABLE_SETTINGS_STRICT = {"intersection_tolerance":3}


def get_y_coords_tables(page):
    print(page.height, page.width)
    if page.height > page.width:
        tables_confined = page.within_bbox(PORTRAIT_COORDS).find_tables(table_settings=TABLE_SETTINGS_STRICT)
        dx1, _, dx2, _ = (PORTRAIT_COORDS)
    else:
        tables_confined = page.within_bbox(LANDSCAPE_COORDS).find_tables(table_settings=TABLE_SETTINGS_STRICT)
        dx1, _, dx2, _ = (LANDSCAPE_COORDS)
    bbox_og = [tables_confined[i].bbox for i in range(len(tables_confined))]
    bbox_tables = [(dx1, tables_confined[i].bbox[1], dx2, tables_confined[i].bbox[3]) for i in range(len(tables_confined))]
    print("bbox", bbox_tables)
    return bbox_tables

def get_bouding_boxes_text(page, bbox_tables):
    if page.height > page.width:
        dx1, dy1, dx2, dy2 = (PORTRAIT_COORDS)
    else:
        dx1, dy1, dx2, dy2 = (LANDSCAPE_COORDS)
    if not bbox_tables:
        bbox_text = [(dx1, dy1, dx2, dy2)]
    else:
        bbox_text = []
        bbox_text.append((dx1,dy1,dx2,bbox_tables[0][1]))
        for i in range(len(bbox_tables)-1):
            bbox_text.append((dx1,bbox_tables[i][3],dx2,bbox_tables[i+1][1]))
        bbox_text.append((dx1,bbox_tables[-1][3],dx2,dy2))    
    text_on_page = []
    
    for i in bbox_text:
        text = page.within_bbox(i).extract_text()
        text_on_page.append(text)
        
    return bbox_text, text_on_page

def get_tables(page, bbox_tables): 
    tables = []
    for i in bbox_tables:
        i = (i[0]-TABLE_EXPANSION_HORIZONTAL,i[1]-TABLE_EXPANSION_VERTICAL,i[2]+TABLE_EXPANSION_HORIZONTAL,i[3]+TABLE_EXPANSION_VERTICAL)
        table = page.crop(i).extract_tables(table_settings=TABLE_SETTINGS_LINEANT)
        tables.append(table)
    return tables




def get_annex_page(pdf_path, start=0):
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=start):
            print(f"Page {page_number}:")
            if page.height > page.width:
                raw = page.within_bbox(PORTRAIT_COORDS).extract_text() #Dev self engineered parameters
            else:
                raw = page.within_bbox(LANDSCAPE_COORDS).extract_text() #Dev self engineered parameters
            if not raw:
                continue
            if "ANNEX" in raw:
                annex_present_on_page = page_number
                return annex_present_on_page
    return None

def process_page(page):
    bbox_tables = get_y_coords_tables(page)
    tables = get_tables(page, bbox_tables)
    bbox_text, text_on_page = get_bouding_boxes_text(page, bbox_tables)
    elements = []

    # Add text elements
    for bbox, text in zip(bbox_text, text_on_page):
        if text.strip():
            elements.append((bbox[1], {"Text": text.strip()}))  # bbox[1] is the y-coordinate

    # Add table elements
    for bbox, table in zip(bbox_tables, tables):
        elements.append((bbox[1], {"Table": table}))  # bbox[1] is the y-coordinate

    # Sort elements by y-coordinate (second index of bounding box)
    elements.sort(key=lambda x: x[0])

    content = []
    for element in elements:
        content.append(element[1])
    # Create the final ordered dictionary
    return content

def post_process_contents(content):
    major_content = []

    for page in content:
        for element in page:
            if major_content and "Text" in major_content[-1] and "Text" in element:
                major_content[-1]["Text"] += " " + element["Text"]
            elif "Table" in element:
                if major_content and "Table" in major_content[-1]:
                    major_content[-1]["Table"].extend(element["Table"][0])
                else:
                    major_content.append({"Table": element["Table"][0]})
            else:
                major_content.append(element)
                
    for item in major_content:
        if "Text" in item:
            item["Text"] = get_display(item["Text"])
        else:
            for row in item["Table"]:
                for i in range(len(row)):  # Iterate using index to modify in place
                    row[i] = get_display(row[i]) if row[i] else ""
    return major_content



def process_pdf(pdf_path):
    start = get_annex_page(pdf_path) if get_annex_page(pdf_path) else 0
    main_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(start, len(pdf.pages)):
            page = pdf.pages[i]
            print(f"Page {i}:")
            content = process_page(page)
            main_content.append(content)
    final_main_content = post_process_contents(main_content)
    return final_main_content


# filename = "20241517"
# pdf_path = f"PDF/{filename}.pdf"

# json_output = process_pdf(pdf_path)

# with open(f"pdf_plumber/Results/{filename}_reverse.json", "w") as file:
#     json.dump(json_output, file, ensure_ascii=False, indent=4)