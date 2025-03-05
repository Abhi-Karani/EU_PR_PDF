import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_prompts as eu_prompts
import utils.eu_utils.eu_url_parser_utils as eu_url_parser_utils
import pandas as pd
import json

from service.logger.logger import get_logger
logger = get_logger("eu_name_extractor_utils")

def perform_name_changetype_extraction(full_content_html):
        content = eu_url_parser_utils.normalize_content(full_content_html)
        i = 1
        try:
            response_extractor_names_call = get_names_extractor_output(content) 
            output_list, i = check_for_overflowing_context_limit_calls_names(content, response_extractor_names_call, i)
            output_names_changeType = output_list  #return this if required to extract
            return output_names_changeType, i
        except Exception as E:
            logger.error(f"Error in perform name changetype extraction: {E}")
            raise Exception(f"Error in perform name changetype extraction: {E}")

def get_names_extractor_output(content):
    try:
        response_extractor_names_call = eu_common_utils.retry_llm_calls_with_constant_delay(eu_common_utils.get_messages(
                                                                                    get_content_names(content),
                                                                                    eu_prompts.name_extractor_prompt
                                                                                    )
                                                                                )

        return response_extractor_names_call
    except Exception as E:
        logger.error(f"Error in get_names_extractor_output first LLM call to get name,changetype: {E}") 
        raise Exception(f"Error in get_names_extractor_output first LLM call to get name,changetype: {E}") 

def check_for_overflowing_context_limit_calls_names(content, response_extractor_names_call, i):
    intermediate_op_list_flag = "in_progress"
    output_message = response_extractor_names_call
    output_list = []
    try:
        while intermediate_op_list_flag == "in_progress":
            last_entity, intermediate_op_list, intermediate_op_list_flag = curate_intermediate_output_list_names(
                                                                                                    output_message, 
                                                                                                    output_list
                                                                                                    )
            if intermediate_op_list_flag == "completed" and intermediate_op_list is not None:
                logger.info("Extraction is completed!!")
                output_list = intermediate_op_list
            elif intermediate_op_list_flag == "in_progress" and intermediate_op_list is not None:
                logger.info("Making an LLM call with restructured prompt!!")
                i += 1
                response_extractor_subsequent_calls = get_names_extractor_output_subsequent(content, last_entity)
                output_message = response_extractor_subsequent_calls
                output_list = intermediate_op_list
                #There is no flag for repeating entities here
            else:
                logger.error(f"There was an error could not update the list further, list uptill now is: {intermediate_op_list}")
                return intermediate_op_list, i
        return output_list, i
    except Exception as E:
        logger.error(f"Error in check for overflowing context limit for names: {E}")
        raise Exception(f"Error in check for overflowing context limit for names: {E}")

def get_content_names(content):
    return f"content: {content}"

def get_content_names_subsequent(webpage_content, last_entity):
    return (
        f"content: {webpage_content}\n\n"
        f"last_entry_extracted: {last_entity}"
        )
    
def curate_intermediate_output_list_names(chat_completions, output_list):
    """
        inputs: LLM output, output list
        output: lastentity, Updated output list, completion_flag
    """
    stop_reason = eu_common_utils.get_stop_reason_from_llm_response(chat_completions)
    text_content = eu_common_utils.get_text_from_llm_response(chat_completions)

    logger.info(f"Output text string is: \n{text_content}")
    logger.info(f"Output stop_reason is: {stop_reason}")

    if stop_reason == 'length':
        try:
            logger.info("Notify analyst to verify this output as an additional layer of safety.")
            last_entity, updated_intermediate_output_list = update_intermediate_output_list_with_new_entries_names(output_list, text_content)
            return last_entity,updated_intermediate_output_list, "in_progress"
        except Exception as e:
            logger.error(f"LLM response has stop_reason == 'length' but json.loads failed. Error: {e}")
            return None, None, "completed"
    
    elif stop_reason == 'stop':
        try:
            logger.info("LLM terminated gracefully")
            temp_output_list = json.loads(text_content)
            temp_output_list = temp_output_list.get("result")
            if temp_output_list is None:
                raise ValueError("The 'result' key is missing in the JSON content.")
            output_list.extend(temp_output_list)
            return None, output_list, "completed"
        except Exception as e:
            logger.error(f"LLM response has stop_reason == 'stop' but still json.loads failed. Error: {e}")
            return None, None, "completed"
    else:
        logger.info(f"LLM has stopped due to unknown reason: {stop_reason}")
        return None, None, "completed"
    
def update_intermediate_output_list_with_new_entries_names(output_list, json_text_content):
    """
        input: output list, LLM_output
        output: last_entity, updated list
    """
    try:
        json_text_content, last_entity = get_json_parsable_string_from_llm_output_names(json_text_content)
    except Exception as e:
        raise Exception(f"Error occurred while update_intermediate_output_list_with_new_entries_names in get_json_parsable_string_from_llm_output_names{e}")
    try:            
        temp_output_list = json.loads(json_text_content)
        temp_output_list = temp_output_list.get("result")
        if temp_output_list is None:
            raise ValueError("The 'result' key is missing in the JSON content.")
        
        logger.info(f"Last entry is:{last_entity}")
        logger.info(f"Total entries in output_list pre-update: {len(output_list)}")
        logger.info(f"Total entries in this update: {len(temp_output_list)}")
        output_list.extend(temp_output_list)
        logger.info(f"Total entries in output_list post-update: {len(output_list)}")

        return last_entity, output_list                
    except Exception as e:
        logger.error(f"Error occurred while updating output list: {e} sending the old output list") 
        return last_entity, output_list 
# in some case if there are 100 entities, and output list could not be updated because of some reason for
# 23-40 entities then does it make sense to stop the LLM there are not continue from 40-100 onwards ?
# maybe they weren't related to sanctions and will be skipped by the data_point extractor as well ? will need review
#Todo need review
      
def get_json_parsable_string_from_llm_output_names(data: str):
    """ input: string, 
        output: json parsable string, last entity 
    """
    try:
        lines = data.strip().split('\n')
        found_comma = False
        # Loop through lines in reverse to find the last line with a comma
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.endswith(','):
                found_comma = True
                last_complete_entity = line
                break
        if found_comma:
            output_lines = lines[:i+1]
            output_string = '\n'.join(output_lines)
            # Add the closing brackets to make it a valid JSON
            output_string_ready_for_json_loads = output_string[:-1] + "}]}"
            return output_string_ready_for_json_loads, last_complete_entity
        else:
            logger.error(f"No ',' found in the data. {data}")
            raise Exception(f"No ',' found in the data. {data}")
    except Exception as E:
        logger.error(f"Error in getting json parsable string from llm output names: {E} input is {data}")
        raise Exception(f"Error in getting json parsable string from llm output names: {E} input is {data}")
    
def get_names_extractor_output_subsequent(content, last_entity):
    response_extractor_names_call = eu_common_utils.retry_llm_calls_with_constant_delay(eu_common_utils.get_messages(
                                                                                get_content_names_subsequent(content, last_entity),
                                                                                eu_prompts.name_extractor_prompt_sub
                                                                                )
                                                                            )

    return response_extractor_names_call