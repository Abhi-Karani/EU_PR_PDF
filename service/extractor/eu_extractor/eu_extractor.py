
# import os
from utils.eu_utils.eu_url_parser_utils import perform_token_check, copy_html_soup
# from utils.eu_utils.eu_name_extractor_utils import perform_name_changetype_extraction
# from utils.eu_utils.eu_common_utils import convert_output_of_names_changetype_call_to_df, final_output_to_data_frame, compare_dfs_and_get_output_in_json, LLMFault
# from utils.eu_utils.eu_data_point_extractor_utils import perform_data_point_extraction
# from utils.eu_utils.eu_common_utils import category_filter
# Init logger with file name
from service.logger.logger import get_logger
import asyncio
logger = get_logger("eu_extractor")

# retriable_errors = (LLMFault, Exception)
# def retry_if_llm_fault_issue(details):
#     logger.info(f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries. Exception: {details['exception']}")


# def extractor(press_release_record, full_content_html):
#     loop = asyncio.get_event_loop()
#     json_obj = loop.run_until_complete(extract_records(press_release_record, full_content_html))
#     return json_obj

def extract_records(json_file):
    # Get list id from env
    # list_id = os.getenv("LIST_ID", None)
    # logger.info("Starting extraction for EU, List ID : %s", list_id)
    
    
    context_call = ""
    table_count = 0
    for i in json_file:
        if "Text" in i:
            context_call += "\n"+i.get("Text")
        else:
            context_call += "\n"+f"Table {table_count}"
            table_count+=1
    
    print(context_call)
    
    perform_token_check(str(context_call), "gpt-4") 
    
    # html_name_change_type = copy_html_soup(full_content_html)
    # output_names_change_type, llm_call_count = perform_name_changetype_extraction(html_name_change_type)
    # names_data_frame = convert_output_of_names_changetype_call_to_df(output_names_change_type)
    # # llm_call_count = 0
    # html_data_point = copy_html_soup(full_content_html)
    # final_output_list, llm_call_count, image_links = await perform_data_point_extraction(html_data_point,llm_call_count)
    # final_output_data_frame = final_output_to_data_frame(final_output_list, image_links)

    # logger.info(f"Total LLM calls made: {llm_call_count}")
    # json_obj = compare_dfs_and_get_output_in_json(final_output_data_frame, names_data_frame)
    
    # return json_obj