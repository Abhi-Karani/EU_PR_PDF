
formats_date_of_listings = ["date of listing"]

def is_header_row(row):
    if row[-1].strip().lower() in formats_date_of_listings:
        return True
    else:
        return False

def is_complete_row(row_curr):
    if row_curr[0].strip():
        return True
    return False

def append_header_row(header_row, row):
    export_row = [""] * len(header_row)
    if not header_row:
        export_row = row
        return export_row
    for cell in range(len(header_row)):
        if row[cell]:
            export_row[cell] = header_row[cell] + ": " + row[cell]
        else:
            export_row[cell] = header_row[cell] + ": "
    return export_row               

def modify_prev_row(prev_row, new_row):
    export_row = [""] * len(prev_row)
    for cell in range(len(prev_row)):
        if new_row[cell]:
            export_row[cell] = prev_row[cell] + "\n" + new_row[cell]
        else:
            export_row[cell] = prev_row[cell]
    return export_row

def clean_json_tables(json_input):
    json_output = []
    for item in json_input:
        if "Text" in item:
            json_output.append(item)
            continue
        table = item.get("Table", [])
        cleaned_table = []
        header_row = ""
        for row_num in range(len(table)):
            if is_header_row(table[row_num]):
                header_row = table[row_num]
                continue
            
            if not cleaned_table:
                temp_row = append_header_row(header_row, table[row_num])
                cleaned_table.append(temp_row)
                continue
                
            if is_complete_row(row_curr=table[row_num]):
                temp_row = append_header_row(header_row, table[row_num])
                cleaned_table.append(temp_row)
            else:
                temp_row = modify_prev_row(cleaned_table.pop(), table[row_num])
                cleaned_table.append(temp_row)
        json_output.append({"Table": cleaned_table})
    return json_output