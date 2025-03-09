
# import os
from utils.eu_utils.eu_url_parser_utils import perform_token_check, copy_html_soup
import utils.eu_utils.eu_process_name_aliases as alias_utils
import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_prompts as prompts
from service.logger.logger import get_logger
import json

import asyncio
logger = get_logger("eu_extractor")

def extract_context(context_call):
    perform_token_check(str(context_call), "gpt-4") 
    
    table_context = alias_utils.llm_call_and_parse_json_dict_response(eu_common_utils.get_messages(context_call, prompts.context_call))
    return table_context