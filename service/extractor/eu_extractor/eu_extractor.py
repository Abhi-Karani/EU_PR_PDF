
import os
from utils.eu_utils.eu_url_parser_utils import perform_token_check, copy_html_soup
from utils.eu_utils.eu_name_extractor_utils import perform_name_changetype_extraction
from utils.eu_utils.eu_common_utils import convert_output_of_names_changetype_call_to_df, final_output_to_data_frame, compare_dfs_and_get_output_in_json, LLMFault
import utils.eu_utils.eu_data_point_extractor_utils as extractor_utils
import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_prompts as prompts
# Init logger with file name
from service.logger.logger import get_logger
import json

import asyncio
logger = get_logger("eu_extractor")

retriable_errors = (LLMFault, Exception)
def retry_if_llm_fault_issue(details):
    logger.info(f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries. Exception: {details['exception']}")


def extractor(press_release_record, full_content_html):
    loop = asyncio.get_event_loop()
    json_obj = loop.run_until_complete(extract_records(press_release_record, full_content_html))
    return json_obj

async def extract_records(context):
    superset_records = []

    for key,value in context.items():
        if "Table" in key:
            output_list = await extractor_utils.parallelized_processing(value)
            superset_records.extend(output_list)
    

    # logger.info(f"Total LLM calls made: {llm_call_count}")
    # json_obj = compare_dfs_and_get_output_in_json(final_output_data_frame, names_data_frame)
    
    # return json_obj