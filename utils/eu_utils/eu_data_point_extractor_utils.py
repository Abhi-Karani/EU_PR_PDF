import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_url_parser_utils as eu_url_parser_utils
from utils.eu_utils.eu_pydantic_utils import execute_lang_chain, output_format_records, open_ai_llm
from utils.eu_utils.eu_process_name_aliases import permute_names, adjust_for_names
import utils.eu_utils.eu_prompts as eu_prompts
import json
import itertools
import re
from service.logger.logger import get_logger
import asyncio
logger = get_logger("eu_data_point_extractor_utils")

def modify_additional_info_incase_of_rows(is_row,data_present_in_content, input_content_for_LLM_call):
    try:
        if not is_row:
            return data_present_in_content
        for entry in data_present_in_content:
            try:
                if not isinstance(entry, dict):  # Ensure it's a dictionary before updating
                    logger.error(f"{entry} is not a dictionary")
                else:
                    content_as_soup = eu_url_parser_utils.copy_html_soup(input_content_for_LLM_call)
                    header_removed_row_as_soup = eu_url_parser_utils.remove_the_header_row_from_a_bs_row(content_as_soup)
                    replaced_row = header_removed_row_as_soup.get_text(strip=True, separator=" ")
                    entry["completeInformation"] = replaced_row
            except Exception as E:
                logger.error(f"Error in modify_additional_info_incase_of_rows for entry: {entry}, error: {E}")
    except Exception as E:
        logger.error(f"Error in modify_additional_info_incase_of_rows error: {E}")
    return data_present_in_content
    
    
def get_name_adjusted_records(output_message):
    try:    
        temp_output_list = json.loads(output_message)
        temp_output_list = temp_output_list.get("result")
        if not temp_output_list:
            return []
        temp_output_list = adjust_for_names(temp_output_list)
        temp_output_list = permute_names(temp_output_list)
        logger.info(f"Total number of entries in this content: {len(temp_output_list)}")
        return temp_output_list              
    except Exception as e:
        logger.error(f"Error occurred while get_name_adjusted_records: {e}")
        return []
    
def extract_complete_records(output_message,costs):
    extract_content_again = True
    list_of_records_in_content = []
    try:
        if costs.completion_tokens < eu_common_utils.max_tokens:
            logger.info("LLM has stoped gracefully")
            list_of_records_in_content.extend(get_name_adjusted_records(output_message))
            extract_content_again = False
        else:
            logger.info("LLM has stoped unexpectedly")
            output_message_modified = get_json_parsable_string_from_llm_output(output_message)
            list_of_records_in_content.extend(get_name_adjusted_records(output_message_modified))
        return list_of_records_in_content, extract_content_again
    except Exception as E:
        logger.error(f"Error occurred while extract_complete_records: {E}, costs: {costs}, llm_response: {output_message}")


def process_content(input_content_for_LLM_call):
    list_of_records_in_content= []
    should_extract_content = True
    try:
        while(should_extract_content == True):
            last_entity = list_of_records_in_content[-1]
            prompt_for_call = eu_prompts.extractor_system_prompt if not last_entity else eu_prompts.extractor_system_prompt_3_7
            input_for_call = f"*Input*: {input_content_for_LLM_call}" if not last_entity else f"""*Input*: {input_content_for_LLM_call}\n*Last Entity*: {last_entity.get("name", "")}"""

            output_message,costs = execute_lang_chain(system_prompt=prompt_for_call, 
                                                    format_instructions=output_format_records,
                                                    input_content=input_for_call, 
                                                    model=open_ai_llm)
            records_extracted, should_extract_content = extract_complete_records(output_message, costs)
            list_of_records_in_content.extend(records_extracted)
    except Exception as E:
        logger.error(f"Error in process_content for content: {input_content_for_LLM_call} as error: {E}")
    return list_of_records_in_content

async def parallelized_processing(contents):
    individuals_data_full = []
    
    # Use asyncio.to_thread to run blocking tasks in parallel
    tasks = [asyncio.to_thread(process_content, content) for content in contents]
    
    # Gather results concurrently
    results = await asyncio.gather(*tasks)
    
    # Collect all individual results
    for individuals_data in results:
        individuals_data_full.extend(individuals_data)

    final_output_list = individuals_data_full
    return final_output_list

def get_json_parsable_string_from_llm_output(data: str):
    """ input: string, 
        output: json parsable string
    """
    try:
        lines = data.strip().split('\n')
        found_brace = False
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '},' and 'id_remarks' not in lines[i - 1] and "wholeNameVariations" not in lines[i-1]:
                found_brace = True
                break

        if found_brace:
            output_lines = lines[:i+1]
            output_string = '\n'.join(output_lines)
            output_string_ready_for_json_loads = output_string[:-1] + "]}"
            return output_string_ready_for_json_loads
        else:
            raise Exception(f"No ',' found in the data. {data}")
    except Exception as E:
        raise Exception(f"Error in getting json parsable string from llm output: {E}input is {data}")