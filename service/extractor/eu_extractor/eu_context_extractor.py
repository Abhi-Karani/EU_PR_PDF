
# import os
from utils.eu_utils.eu_url_parser_utils import perform_token_check, copy_html_soup
import utils.eu_utils.eu_data_point_extractor_utils as extractor_utils
import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_prompts as prompts
from service.logger.logger import get_logger
import json

import asyncio
logger = get_logger("eu_extractor")

def extract_context(json_file):
    context_call = ""
    table_count = 0
    for i in json_file:
        if "Text" in i:
            context_call += "\n"+i.get("Text")
        else:
            context_call += "\n"+f"Table {table_count}"
            table_count+=1
        
    perform_token_check(str(context_call), "gpt-4") 
    
    table_context = extractor_utils.llm_call_and_parse_json_dict_response(eu_common_utils.get_messages(context_call, prompts.context_call))
    print(table_context)
    return context_call, table_context