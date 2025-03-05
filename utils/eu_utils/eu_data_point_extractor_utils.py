import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_url_parser_utils as eu_url_parser_utils
from utils.eu_utils.eu_post_process_utils import extract_name_and_title
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
    

def process_content(content_as_dictionary):
    data_present_in_content = []
    num_of_llm_calls_made_in_content = 0
    try:
        # This is the synchronous code that handles each individual content
        if not isinstance(content_as_dictionary, dict):
            raise Exception(f"content is not a dictionary")
        is_row = False
        for key, value in content_as_dictionary.items():
            if key == "row":
                is_row = True
            input_content_for_LLM_call = value
        output_message = get_first_call_output(input_content_for_LLM_call)
        data_present_in_content, num_of_llm_calls_made_in_content = check_for_overflowing_context_limit(
                                                                            data_present_in_content, 
                                                                            input_content_for_LLM_call, 
                                                                            num_of_llm_calls_made_in_content, 
                                                                            output_message
                                                                            )
        data_present_in_content = modify_additional_info_incase_of_rows(is_row,data_present_in_content, input_content_for_LLM_call)
    except Exception as E:
        logger.error(f"Error in process_content for content: {content_as_dictionary} as error: {E}")
    return data_present_in_content

def adjust_for_names(list_of_dicts_containing_data_points):
    try:
        for entry in list_of_dicts_containing_data_points:
            if not isinstance(entry, dict):
                raise Exception(f"entry within LLM output is not a dict {entry}")
            entry_name_alias_extracted = process_name_info_to_get_name_alias_lists(entry)
    except Exception as E:
        logger.error(f"Exception in adjust_for_names, error: {E} for input: {list_of_dicts_containing_data_points}")
    return list_of_dicts_containing_data_points

def llm_call_and_parse_json_dict_response(message):
    try:
        call_message = eu_common_utils.retry_llm_calls_with_constant_delay(message, eu_common_utils.llm_for_name_alias)
        json_call_output_text = eu_common_utils.parse_response_to_json(call_message)
        if not isinstance(json_call_output_text,dict):
            raise Exception(f"json_call_output_text is not a dict: {json_call_output_text}")
        return json_call_output_text
    except Exception as E:
        raise Exception(f"error in llm_call_and_parse_json_dict_response: {E} for input {message}")

def helper_extend_list_with_llm_response(input_list, llm_response):
    if isinstance(llm_response,list):
        input_list.extend(llm_response)
    llm_response_list = eu_common_utils.input_string_array_output_array(llm_response)
    input_list.extend(llm_response_list) if llm_response_list else None
    return input_list

def process_name_info_to_get_name_alias_lists(entry):
    try:
        name_related_info = entry.get("name_info")
        if entry["entityType"] in eu_common_utils.acceptable_values_for_individual:
            first_names, middle_names, last_names, whole_names = [], [], [], []
            part_split_call, pure_impure_call_2, pure_impure_call_1 = {}, {}, {}
            primary_full_name, remaining_string = "", ""
            titles = []

            pure_impure_call_1 = llm_call_and_parse_json_dict_response(eu_common_utils.get_messages(
                                                                                            name_related_info,
                                                                                            eu_prompts.pure_impure_prompt))
            if pure_impure_call_1.get("impure_whole_names"):
                pure_impure_call_2 = llm_call_and_parse_json_dict_response(eu_prompts.pure_impure_call_2(pure_impure_call_1.get("impure_whole_names")))
                remaining_string = pure_impure_call_2.get("remaining_string")
            if remaining_string:
                part_split_call = llm_call_and_parse_json_dict_response(eu_prompts.part_split_call(remaining_string))
                primary_full_name, titles = (part_split_call.get("primaryFullName"),part_split_call.get("titles"))
                whole_names.append(primary_full_name)
                
                target_list = {"first": first_names, "middle": middle_names, "last": last_names}
                for part in part_split_call.get("nameParts", []):
                    target_list.get(part.get("partLabel")).append(part.get("partValue"))
                    helper_extend_list_with_llm_response(target_list.get(part.get("partLabel")), part.get("aliases"))
                    
            for dictionary in [part_split_call, pure_impure_call_2, pure_impure_call_1]:
                for key in ["allFullNameVariants", "nicknames", "pure_whole_names"]:
                    helper_extend_list_with_llm_response(whole_names, dictionary.get(key))
            
            entry["name_alias_info"] = {
                                        "titles": titles,
                                        "primaryName":primary_full_name,
                                        "wholeNameVariations":whole_names,
                                        "firstNameVariations":first_names,
                                        "middleNameVariations":middle_names,
                                        "lastNameVariations":last_names
                                        } 
        else:
            primary_name_dict = llm_call_and_parse_json_dict_response(eu_common_utils.get_messages(
                                                                                            name_related_info,
                                                                                            eu_prompts.primary_name_entities))
            entry["name"] = primary_name_dict.get("primary_name") if primary_name_dict.get("primary_name") not in eu_common_utils.not_expected_outcomes else entry["name"]
            entry["name_alias_info"] = llm_call_and_parse_json_dict_response(eu_common_utils.get_messages(name_related_info, 
                                                                                    eu_prompts.name_alias_for_entities_prompt))
    except Exception as E:
        logger.error(f"Exception in process_name_info_to_get_name_alias_lists, error: {E} for input: {entry}")
    return entry

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

async def perform_data_point_extraction(fullcontenthtml,i):
    try:
        contents, _, image_links= eu_url_parser_utils.get_html_text_oj_tables_seperate(fullcontenthtml) #html is passed to tables
        final_output_list = await parallelized_processing(contents)
        return final_output_list, i, image_links
    except Exception as E:
        raise Exception(f"Error in perform_data_point_extraction: {E}")
    
def get_first_call_output(content):
    try:
        response_extractor_first_call = eu_common_utils.retry_llm_calls_with_constant_delay(eu_common_utils.get_messages(
                                                                                f"content: {content}",
                                                                                f"""{eu_prompts.data_point_extractor_system_prompt_1}\n\nData Points: {eu_prompts.data_points_extractor}"""
                                                                                    )
                                                                            )
        return response_extractor_first_call 
    except Exception as E:
        raise Exception(f"error in get_first_call_output: {E}")

def get_content_extractor_first_call(webpage_content, data_points_extractor):
    return (
        f"content: {webpage_content}\n\n"
        f"Data Points: {data_points_extractor}"
        )

def check_for_overflowing_context_limit(individuals_data, content, i, output_message):
    intermediate_op_list_flag = "in_progress"
    output_list = []
    try:
        while intermediate_op_list_flag == "in_progress":
            last_entity,intermediate_op_list, intermediate_op_list_flag = curate_intermediate_output_list( 
                                                                                                    output_message, 
                                                                                                    output_list
                                                                                                    )
            if intermediate_op_list_flag == "completed" and intermediate_op_list is not None:
                logger.info("Extraction is completed!!")
                output_list = intermediate_op_list
            elif intermediate_op_list_flag == "in_progress" and intermediate_op_list is not None:
                logger.info("Making an LLM call with restructured prompt!!")
                i += 1
                response_extractor_subsequent_calls = get_subsequent_calls_output(content, last_entity)
                output_message = response_extractor_subsequent_calls
                output_list = intermediate_op_list

            if eu_common_utils.check_duplicate_names(output_list): #todo review needed what should i do here if the function fails
                raise eu_common_utils.LLMFault("There are duplicates in this LLM call list ask the analyst to verify crucial","duplication")
            # - if duplicate_extraction observed - raise an exception anda notif for a manual run
            # - set a hard limit on number of calls allowed, based on the tokens (check the backtested o/p tokens)
        
        logger.info(f"Number of LLM calls made uptill this annex/content: {i}")
        individuals_data.extend(output_list)
        if eu_common_utils.check_duplicate_names(individuals_data):
            logger.info("There are duplicates in list for all annex contents ask the analyst to verify")
            #TODO:- raising a notif to the analyst, details_of_notif - 2 types of duplications, one being crucial when duplicate extractions are due to older data and amended data of an individual resp
            #- we can provide the duplicated records to the analyst
        return individuals_data, i
    except Exception as E:
        raise Exception(f"Error in check for overflowing context limit: {E}")

def curate_intermediate_output_list(chat_completions, output_list):
    """
        inputs: LLM output, output list
        output: lastentity, Updated output list, completion_flag
    """
    stop_reason = eu_common_utils.get_stop_reason_from_llm_response(chat_completions)
    text_content = eu_common_utils.get_text_from_llm_response(chat_completions)

    logger.info(f"Output text string is: \n{text_content}")
    logger.info(f"Output stop_reason is: {stop_reason}")

    if stop_reason == 'length':
        logger.info("Notify analyst to verify this output as an additional layer of safety.")
        last_entity, updated_intermediate_output_list = update_intermediate_output_list_with_new_entries(output_list, text_content)
        if last_entity is None: #The output stoped due to context limit but there is no last entity
            logger.info("The output stoped due to context limit but output list could not be updated")
            return None, updated_intermediate_output_list, "completed"
        return last_entity,updated_intermediate_output_list, "in_progress"
    #Todo review if there is some issue with updating the output list with new entries then we stop the extraction, but we pass the number of entries extracted till now in the output list
    
    elif stop_reason == 'stop':
        logger.info("LLM terminated gracefully")
        try:
            temp_output_list = json.loads(text_content)
            temp_output_list = temp_output_list.get("result")
            if temp_output_list is None:
                raise ValueError("The 'result' key is missing in the JSON content.")
            temp_output_list = adjust_for_names(temp_output_list)
            temp_output_list = permute_names(temp_output_list)
            output_list.extend(temp_output_list)
            return None, output_list, "completed"
        except Exception as e:
            logger.error(f"LLM response has stop_reason == 'stop' in curate_intermediate_output_list but still json.loads failed. Error: {e}")
            return None, output_list, "completed"
    else:
        logger.info(f"LLM has stopped due to unknown reason: {stop_reason}")
        return None, output_list, "completed"

def update_intermediate_output_list_with_new_entries(output_list, json_text_content):
    try:
        json_text_content = get_json_parsable_string_from_llm_output(json_text_content)
        temp_output_list = json.loads(json_text_content)
        temp_output_list = temp_output_list.get("result")
        if temp_output_list is None:
            raise ValueError("The 'result' key is missing in the JSON content.")
        temp_output_list = adjust_for_names(temp_output_list)
        temp_output_list = permute_names(temp_output_list)
        last_entity = temp_output_list[-1]
        last_entity = last_entity.get("name")
        logger.info(f"Last entry is:{last_entity}")
        logger.info(f"Total entries in output_list pre-update: {len(output_list)}")
        logger.info(f"Total entries in this update: {len(temp_output_list)}")

        output_list.extend(temp_output_list)
        logger.info(f"Total entries in output_list post-update: {len(output_list)}")

        return last_entity, output_list                
    except Exception as e:
        logger.error(f"Error occurred while update_intermediate_output_list_with_new_entries: {e}")
        return None, output_list  # Return None to indicate an error
    
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

def name_type_latin_non_latin_mix(name):
    tokens = name.split()  # Tokenize the name by spaces
    all_tokens_are_latin = True
    all_tokens_are_non_latin = True
    
    for token in tokens:
        token_is_latin = True
        for char in token:
            if not eu_common_utils.is_latin(char) and char not in eu_common_utils.list_of_symbols_names_can_have:
                token_is_latin = False
                break
        if token_is_latin:
            all_tokens_are_non_latin = False
        else:
            all_tokens_are_latin = False
    
    if all_tokens_are_latin:
        return "Latin"
    elif all_tokens_are_non_latin:
        return "Non-Latin"
    else:
        print(f"Mixed tokens in name: {name}")
        return "Mixed"

def separate_english_non_english(name_list):
    english_list = []
    non_english_list = []
    try:
        for name in name_list:
            if name_type_latin_non_latin_mix(name) == "Latin":
                english_list.append(name)
            elif name_type_latin_non_latin_mix(name) == "Non-Latin":
                non_english_list.append(name)
            else:
                logger.info(f"name: {name} is excluded")
    except Exception as E:
        logger.error(f"Error in separate_english_non_english with input: {name_list} error: {E}")
    return english_list, non_english_list

def permute_lists_names_output_list(first_names, middle_names, last_names, whole_names, whole_names_aliases):
    name_combinations = []
    try:
        name_permutes = list(itertools.product(first_names, middle_names, last_names))
        for list_of_first_middle_last_name in name_permutes:
            full_name = " ".join(list_of_first_middle_last_name)
            result = re.sub(r'\s+', ' ', full_name)
            if result.strip():
                name_combinations.append(result.strip())

        # Extend the list with whole names, if any
        if whole_names:
            name_combinations.extend(whole_names)
        if whole_names_aliases:
            name_combinations.extend(whole_names_aliases)
    except Exception as E:
        logger.error(f"Error in permute_lists_output_list for {first_names}, {middle_names}, {last_names}, {whole_names}, {whole_names_aliases}, Error: {E}")
    return name_combinations 


def generate_names(name_dict, entity_type):
    """
        input is name_info, which is dictinary with 4 lists
        output is all the permuted variations of names
    """
    english_names = []
    non_english_names = []
    try:
    # Check if name_dict is a dictionary
        if isinstance(name_dict, dict) and name_dict:
            # Extract variations from the input dictionary
            first_names = name_dict.get("firstNameVariations", [])
            middle_names = name_dict.get("middleNameVariations", [])
            last_names = name_dict.get("lastNameVariations", [])
            whole_names = name_dict.get("wholeNameVariations", [])
            whole_names_aliases = name_dict.get("wholeNameAliases", [])

            # Filter out empty lists but keep the default empty string for middle names
            first_names = [first_name for first_name in first_names if first_name]
            middle_names = [middle_name for middle_name in middle_names if middle_name]
            middle_names.append("")
            # middle_names = middle_names if middle_names else [""]
            last_names = [last_name for last_name in last_names if last_name]
            if entity_type in eu_common_utils.acceptable_values_for_individual:
                list_of_names_permuted_all_possible_combinations = permute_lists_names_output_list(first_names, 
                                                                middle_names,
                                                                last_names,
                                                                whole_names,
                                                                whole_names_aliases)
                english_names, non_english_names = separate_english_non_english(list_of_names_permuted_all_possible_combinations)
            else:
                for name in whole_names:
                   is_non_english = False
                   for char in name:
                       if not eu_common_utils.is_latin(char) and char not in eu_common_utils.list_of_symbols_names_can_have:
                           non_english_names.append(name)
                           is_non_english = True
                           break
                   if not is_non_english:
                       english_names.append(name)
        else:
            logger.info(f"name_info is not dict it is {type(name_dict)} for {name_dict}")
    except Exception as E:
        logger.error(f"Error in generate_names for dictionary: {name_dict}, Error: {E}")
    return english_names, non_english_names 

def deduplicate_list_of_names_remove_primary_name(names_list, primary_name):
    """
    deduplicate the names list, case insensitive, consider first instance of the duplicate item, remove primary name from the list, 
    also removing titles from both the aliases and primary name
    Args:
        names_list (list)
        primary_name (str)
    """
    try:
        names_dict = {}
        for name in names_list:
            name_without_title,_ = extract_name_and_title(name)
            lower_name = name_without_title.strip().lower()
            if lower_name not in names_dict:
                names_dict[lower_name] = name
        primary_name_without_title,_ = extract_name_and_title(primary_name)
        primary_name_lower = primary_name_without_title.strip().lower()
        names_dict.pop(primary_name_lower, None)
        names_list_deduped = list(names_dict.values())
        return names_list_deduped
    except Exception as E:
        logger.error(f"error in deduplicate_list_of_names_remove_primary_name for list: {names_list} and primary name: {primary_name} with error: {E}")
        return names_list
            
def get_list_of_names(name_dictionary, primary_name, entity_type):
    english_names_list = []
    non_english_names_list = []
    try:
        if name_dictionary not in eu_common_utils.not_expected_outcomes:
            english_names_list, non_english_names_list = generate_names(name_dictionary, entity_type)
        english_names_list_deduped = deduplicate_list_of_names_remove_primary_name(english_names_list, primary_name)
        non_english_names_list_deduped = deduplicate_list_of_names_remove_primary_name(non_english_names_list,primary_name)
    except Exception as E:
        logger.error(f"Error in get_list_of_names for dictionary: {name_dictionary} primary Name: {primary_name}, Error: {E}")
    return english_names_list_deduped, non_english_names_list_deduped

def permute_names(temp_output_lists):  # textcontent should be json parsable
    """
        input: list of dicts
        output: two additional fields aliases and aliases_og that contains the permuted aliases and aliases og
        Assumption: if any error occurs in permuting then, the alaises(_og) will be empty lists, I am not raising any exception
    """
    main = []
    try:
        for record in temp_output_lists:
            primary_name = record.get("name")
            entity_type = record.get("entityType")
            name_info = record.get("name_alias_info")
            name_info_dictionary = None
            if not isinstance(name_info, dict) and isinstance(name_info, str):
                name_info_dictionary = json.loads(name_info)
            elif isinstance(name_info,dict):
                name_info_dictionary = name_info
            english_names_list, non_english_names_list = get_list_of_names(name_info_dictionary, primary_name, entity_type)
            record["aliases"] = english_names_list
            record["aliases_og"] = non_english_names_list
            main.append(record)
        return main
    except Exception as E:
        logger.error(f"Error in permute_names for list: {temp_output_lists}, Error: {E}")
        return temp_output_lists #Todo review should I return the original list in case of unforceen error

def get_subsequent_calls_output(content, last_entity):
    try:    
        response_extractor_subsequent_calls = eu_common_utils.retry_llm_calls_with_constant_delay(eu_common_utils.get_messages(
                                                                                            get_content_extractor_subsequent_calls(
                                                                                                        content,
                                                                                                        last_entity
                                                                                                ),
                                                                                            f"""{eu_prompts.extractor_system_prompt_3_7}\n\ndata_points_extractor: {eu_prompts.data_points_extractor}"""
                                                                                        )
                                                                                        )
        return response_extractor_subsequent_calls
    except Exception as E:
        raise Exception(f"error in get_subsequent_calls_output: {E}, with last_entity:{last_entity}")

def get_content_extractor_subsequent_calls(webpage_content, previously_extracted_body):
    return (
        f"content: {webpage_content}\n\n"
        f"previously_extracted_body: {previously_extracted_body}"
    )