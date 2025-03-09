def format_pdf_output_for_context_call(json_file):
    context_call = ""
    table_count = 0
    for i in json_file:
        if "Text" in i:
            context_call += "\n"+i.get("Text")
        else:
            context_call += "\n"+f"Table {table_count}"
            table_count+=1
    return context_call

def get_table_num_table_dict(cleaned_output_pdf_plumber):
    count = 0
    table_map = {}
    for item in cleaned_output_pdf_plumber:
        if "Table" in item:
            table_map[f"Table {count}"] = item
            count += 1
    return table_map

def add_context_to_each_row_in_table(table, context):
    for row in table: 
        row.append(f"Context: {context}")

def format_context(context, cleaned_output_pdf_plumber):
    table_map = get_table_num_table_dict(cleaned_output_pdf_plumber)
    final_output = []
    for key, value in context.items():
        if "Table" in key:
            for row in table_map.get(key, []): 
                row.append(f"Context: {value}")
            final_output.extend(table_map.get(key, []))
        else:
            final_output.append(f"""Context: {value},
                                Data: {key}""")
    return final_output