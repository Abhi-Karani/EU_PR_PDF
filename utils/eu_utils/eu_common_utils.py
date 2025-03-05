    
import time
from datetime import datetime
from openai import OpenAI
import pandas as pd
from datetime import timezone 
import re
import json
from rapidfuzz.utils import default_process
from rapidfuzz import process, fuzz
import utils.eu_utils.eu_prompts as eu_prompts
import utils.eu_utils.eu_url_parser_utils as eu_url_parser_utils
import os
from service.logger.logger import get_logger
import unicodedata
import ast
logger = get_logger("eu_common_utils")
from config.config import Config

llm = "gpt-4o-2024-05-13" 
llm_for_name_alias = "gpt-4o" 
temperature = 0
max_tokens = 4096
max_retries_constant_delay = 3
retry_delay_constant_delay = 30
client = OpenAI(
    api_key= Config.OPENAI_API_KEY
)

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))

# Open and load the JSON file
with open(os.path.join(root_dir, 'constants', 'common_titles_list.json'), 'r') as file:
    common_titles_list = json.load(file)

with open(os.path.join(root_dir, 'constants', 'country_names_list.json'), 'r') as file:
    country_names_list = json.load(file)

id_mapping_excel_path = os.path.join(root_dir, 'constants', 'ID_mapping.xlsx')
id_mapping_excel_df = pd.read_excel(id_mapping_excel_path)
# Access the lists from the JSON data
country_names_list = country_names_list["country_names_list"]
common_titles = common_titles_list["common_titles"]
country_nationality_excel_path = os.path.join(root_dir, 'constants', 'country_nationality.xlsx')
country_nationality_df = pd.read_excel(country_nationality_excel_path)

acceptable_values_for_individual = ["individual", "Individual", "Person","person","PERSON","INDIVIDUAL"]
unacceptable_id_remarks = ["NA","na","Na", "NAN", "nan", "Nan","NONE", "none", "None"]
unacceptable_entityTypes = {"vessels","vessel"}

def category_filter(full_content_html, url):
    try:
        category = eu_url_parser_utils.get_category(full_content_html)
        logger.info(f"url: {url} is of {category}")
        if category == "Category 1" or category == "Category 0":
            logger.error(f"This url belongs to {category}. Stopping Extraction")
            raise Exception(f"This url belongs to {category}")
    except Exception as E:
        logger.error(f"error in category_filter {E}. Stopping Extraction")
        raise Exception(f"error in category_filter {E}")



class LLMFault(Exception):
    def __init__(self, message, error):
        self.message = message
        self.error = error #not used
    def __str__(self):
        return self.message
    
class retryException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

Index = ['name', 'aliases', "aliases_og","full_name_info_total",'entityType',
        #  'formerlyKnownAs', 'originalScriptAliasesFormerlyKnownAs',
        'designation', 'placeOfBirth', 'dateOfBirth', 'nationality_Country_Name',"citizenship_Country_Name",
        'gender','idDetails','addressDetails', 'listedOn', 'placeofRegistration',
        'contactInformation', "completeInformation", 'name_alias_info', 'originalScriptName', 'name_info',"imageNumbers"]

not_expected_outcomes = [["NA"], "[]", "['NA']","","nan", None, [""], "NAN", "null", "na", "NA", "Na", "['']",[],{}]

exempt_from_mongo = [None, [], {}]

def llm_call_open_ai(message, model):   #defining an LLM call
    try:
        start_dt = datetime.now()
        logger.info(f"LLM started: {start_dt}")
        response = client.chat.completions.create(
                                                model=model, 
                                                max_tokens=max_tokens,
                                                response_format={ "type": "json_object" }, #gpt-4o , gpt-4-turbo , or gpt-3.5-turbo
                                                temperature=temperature, 
                                                messages=message
                                                )
        logger.info(f"LLM ended: {datetime.now()}")
        logger.info(f"Response time: {datetime.now() - start_dt} secs")
        return response
    except Exception as e:
        logger.error(f"LLM API error as {e}: {datetime.now()}\nResponse time: {datetime.now() - start_dt} secs")
        return None

def retry_llm_calls_with_constant_delay(message, model=llm):
    retries = 0
    while retries < max_retries_constant_delay:
        response = llm_call_open_ai(message, model=model)
        if response is not None:
            return response
        else:
            time.sleep(retry_delay_constant_delay)
            retries += 1
    logger.error("Max retries reached. Unable to get a successful response.")
    raise Exception(f"Max LLM calls with constant delay retries reached. Unable to get a successful response.")

def get_messages(content, system_prompt):
    messages=[
        {
                "role":"system",
                "content":f"""{system_prompt}"""
            },
        {
            "role": "user",
            "content":  f"""{content}"""
        }
    ]
    return messages

def get_text_from_llm_response(chat_completions):
    return chat_completions.choices[0].message.content
    
def get_stop_reason_from_llm_response(chat_completions):
    return chat_completions.choices[0].finish_reason

def parse_response_to_json(response):
    try:
        response_content = get_text_from_llm_response(response)
        return json.loads(response_content)
    except Exception as e:
        raise Exception(f"Failed to parse response: {response} into JSON, with error: {e}")

def check_duplicate_names(output_list):
    try:
        names = [data.get('name') for data in output_list if data.get('name') != 'NA' and data.get('name') != "ALL"] #if output list is empty names will be empty#if output list is empty names will be empty
        if len(names) == len(set(names)):
            return False  # Names are unique
        else:
            return True  # Names are not unique
    except Exception as E:
        raise Exception(f"error in check_duplicate_names, E: {E}")

def union_values(series):
    filtered_series = series[series != 'NA']
    return ', '.join(filtered_series.astype(str).unique())

def clean_df(df):
    try:
        df = df.groupby('name').agg(lambda x: union_values(x)).reset_index() # dedup with merge
        df = df.applymap(lambda x: pd.NA if x in not_expected_outcomes else x)
        df = df[df['name'].notna()]
        return df
    except Exception as E:
        raise Exception(f"Error in clean_df {E}")
    
def replace_img_with_imglinks(df, dictionary):
    try:
        for key, value in dictionary.items():
            df = df.applymap(lambda x: x.replace(key, value) if isinstance(x, str) else x) 
        return df
    except Exception as E:
        logger.error(f"Error in replace_img_with_imglinks: {E}, for df: {df}, dictionary: {dictionary}")
        return df
    
def convert_output_of_names_changetype_call_to_df(output_names_change):
    df_names = pd.DataFrame(columns=["name", "change_type_flag"]) #init empty df with columns
    try:
        if output_names_change: #there is something in result tab
            for i in range(len(output_names_change)):
                temp = pd.DataFrame(list(output_names_change[i].items()), columns=["name", "change_type_flag"])
                df_names = pd.concat([df_names, temp],ignore_index = True)
    
        logger.info(f"""Total number of individuals/entities names extracted: {df_names.shape[0]}""")
        logger.info("Names extraction has completed")
        return df_names
    except Exception as E:
        raise Exception(f"Error while converting name:changetype pairs to df: {E}")

def final_output_to_data_frame(final_output_list, image_links):
    try:
        df = pd.DataFrame(columns=Index)
        logger.info(f"final_output_list is: {final_output_list}")
        if final_output_list:
            df = pd.DataFrame(final_output_list)
            for col in Index:
                if col not in df.columns:
                    df[col] = "NA"  # Add missing column with "NA"
            df = df[Index]
            df = clean_df(df)
        # Apply the function
        df = replace_img_with_imglinks(df, image_links)
        return df
    except Exception as E:
        raise Exception(f"Error while converting individual/entity output dictionaries to df: {E}")

def remove_leading_zeros(num_str):
    # Check if the input is a valid number string
    if not num_str.isdigit():
        logger.error(f"Invalid input. {num_str}")
        raise Exception(f"Invalid input. {num_str}")

    # Remove leading zeros
    return str(int(num_str))

def update_pr(pr):
    pr["isExtracted"] = True
    pr["updatedDateTime"] = datetime.now(timezone.utc).isoformat(' ', 'seconds')
    pr["updatedUserId"] = "EU_PRESS_LLM_EXTRACTOR_LAMBDA"
    pr["extractedDateTime"]= datetime.now(timezone.utc).isoformat(' ', 'seconds')
    pr["extractedUserId"] =  "EU_PRESS_LLM_EXTRACTOR_LAMBDA"
    pr["status"] = "PR_ENTITY_EXTRACTED"
    pr.pop('_id', None)
    return pr

def update_exception(pr, exc):
    pr["status"] = "FAILED_PR_ENTITY_EXTRACTED"
    pr['error'] = exc
    pr['errorCount']+= pr.get('errorCount',0)
    error = {
        "error_id":pr.get("_id"),
        "error": pr.get('error'),
        "status":pr.get("status")
    }
    pr["failed"] = True
    return pr, error

def get_numbertit_and_listentry(pr):
    try:
        number_title = str(pr.get("numberTitle", ""))
        logger.info(f"the number title is: {number_title}")
        pattern = r'^\d{4}/\d+$'
        if not re.match(pattern, number_title):
            raise Exception(f"Invalid number title format: {number_title}")
        listentryidfirsthalf = pr.get("listEntryIdFirstHalf")
        return number_title,listentryidfirsthalf
    except Exception as E:
        raise Exception(f"Error in get_numbertit_and_listentry: {E}")

def input_string_array_output_array(arr): #return array of strings
    if arr in not_expected_outcomes:
        return None
    if not isinstance(arr,str):
        logger.info(f"arr is not a string: {arr}")
        return None
    if arr:
        try:
            arr_list = ast.literal_eval(arr)
            if isinstance(arr_list,list):
                return arr_list
            else:
                raise Exception(f"array after ast.literal eval is not a list: {arr} and {arr_list}")
        except Exception as E:
            arr = arr.strip().strip("[]")
            split_arr = re.split(r"',\s?'|',\s?\"|\",\s?'|\",\s?\"", arr)
            split_arr = [s.strip().strip("'\"") for s in split_arr]
            return split_arr
    else:
        return None
    
def replace_image_from_string(input_string):
    """
    Replaces any "data:// formatted string with "" 
    Args: 
        input_string
    returns:
        input_string(without "data://....")
    """
    try:
        base64_pattern = r"data:image[^ ]+"  # Pattern stops when a space is encountered
        if re.search(base64_pattern, input_string):
            return None
        return input_string
    except Exception as E:
        logger.error(f"Error in replace_image_from_string with input{input_string}, E: {E}")
        return None #todo review 

def remove_image_from_each_string_in_a_list_of_string(input_list):
    """
        itterates through a list and replaces image from each of its string
        outputs list without image
    """
    output_list = []
    try:
        if input_list:
            for i in input_list:
                if not isinstance(i, str):
                    logger.info(f"item in input list is not a string{i}")
                else:
                    output_i = replace_image_from_string(i)
                    if output_i:
                        output_list.append(output_i)                
        return output_list
    except Exception as E:
        logger.error(f"Error in remove_image_from_each_string_in_a_list_of_string {E}")
        return output_list

def handle_alphabetic_datestring(datestring):    
    try:
        llm_response = get_text_from_llm_response(
                                retry_llm_calls_with_constant_delay(
                                                            get_messages(datestring, 
                                                            eu_prompts.date_formatting_system_prompt)))

        logger.info("llm_response: %s",llm_response)        
        list_of_date_dicts = json.loads(f"""{llm_response}""")   # what if this does not work
        list_of_date_dicts = list_of_date_dicts['result']
        list_of_formated_dates = []
        for date_dict in list_of_date_dicts:
            day = date_dict['dateOfMonth'].zfill(2)   # Extract the day, month, and year from the dictionary
            month = date_dict['monthOfYear'].zfill(2)
            year = date_dict['year']
        
            formatted_date = f"{day}.{month}.{year}"    # Format the date as "dd.mm.yyyy"
            list_of_formated_dates.append(formatted_date)
        return list_of_formated_dates
    except Exception as E:
        raise Exception(f"Error in handle_alphabetic_datestring for {datestring}, error: {E}")


def convert_to_ddmmyyyy_format(str_listOfDoBs): 
    try:
        if str_listOfDoBs in not_expected_outcomes:
            return None
        if isinstance(str_listOfDoBs, str):
            listOfDoBs = input_string_array_output_array(str_listOfDoBs)
        elif isinstance(str_listOfDoBs, list):
            listOfDoBs = str_listOfDoBs
        else:
            logger.info(f"str_listofDoBs is neither str not list {str_listOfDoBs}")
            return None
        if listOfDoBs is None: 
            return []
        updated_listOfDoBs = []
        for datestring in listOfDoBs:
            if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', datestring):  # Check for the regex pattern of '3.4.2983'
                day, month, year = datestring.split('.')
                day = day.zfill(2)  # Prepend 0 if day or month is not two digits
                month = month.zfill(2)
                formatted_date = f"{day}.{month}.{year}"
                updated_listOfDoBs.append(formatted_date)
                # logger.info(f"Appended {formatted_date}")
            
            elif re.search(r'[a-zA-Z]|\d{4}', datestring):    # Check if the datestring contains any alphabet
                try:
                    list_of_formatted_dates = handle_alphabetic_datestring(datestring)
                    for formatted_date in list_of_formatted_dates:
                        updated_listOfDoBs.append(formatted_date)
                        logger.info(f"Appended {formatted_date}")
                except Exception as e:
                    logger.error(f"Error in function handle_alphabetic_datestring while procesing datestring {datestring}: as {e}")
            # else:
            #     logger.info(f"ALERT: A birthdate got missed - for datestring: {datestring}")
            #     #TODO: Abhi
            #     # what if dd mm yyyy is separated by something that is not dot?
            #     # update the code here after consulting with Gaurav and Product team 
    except Exception as e:
        logger.error(f"Error in function convert_to_ddmmyyyy_format while processing datestring {str_listOfDoBs}, error: {e}")
        return None
    return str(updated_listOfDoBs)


def get_has_all(df):
    try:
        has_all = False
        for name in df["name"]:
            if name=="ALL":
                has_all = True
        return has_all
    except Exception as E:
        raise Exception(f"Error in get_has_all df as: {E}")

def compare_dfs_and_get_output_in_json(df, df_names):
    try:
        logger.info(f"""Names_changetype extractor extracted: {df_names.shape[0]} entities
                Data_point_Extractor extracted: {df.shape[0]} entities""")
        has_all = get_has_all(df)

        if df_names.shape[0] > df.shape[0]:
            raise LLMFault(f"""Data_point_extractor has missed something \n \
                        Names_changetype extractor extracted: {df_names.shape[0]} entities \
                        Data_point_Extractor extracted: {df.shape[0]} entities""",
                        "DataPoints extractor missed")
        else:
            if has_all:
                if (df.shape[0]-1) > df_names.shape[0]:
                    raise LLMFault(f"""names_extractor has missed something \n Extractor has extracted (ALL)\n \
                        Names_changetype extractor extracted: {df_names.shape[0]} entities \
                        Data_point_Extractor extracted: {df.shape[0]} entities including ALL""", "Names extractor missed")
            else:
                if (df.shape[0]) > df_names.shape[0]:
                    raise LLMFault(f"""names_extractor has missed something \n \
                        Names_changetype extractor extracted: {df_names.shape[0]} entities \
                        Data_point_Extractor extracted: {df.shape[0]} entities""", "Names extractor missed")

        df_merged = fuzzy_merge_names(df, df_names, threshold=50)

        json_str = df_merged.to_json(orient='records') 
        # Load the JSON string into a Python object
        json_obj = json.loads(json_str)
        return json_obj
    except LLMFault as llmfault:
        logger.error(f"LLM Fault as: {llmfault}")
        raise llmfault
    except Exception as E:
        logger.error(f"Error in compare_dfs_and_get_output_in_json as: {E}")
        raise Exception(f"Error in compare_dfs_and_get_output_in_json as: {E}")

def fuzzy_merge_names(df, df_names, threshold=95): 
    try:
        df_names['change_type_flag'] = df_names.apply(lambda row: str(row['change_type_flag'])+"$$$$"+ str(row.name), axis=1) #O(N)
        # Convert dataframe columns to dictionary
        temp_dict = dict(zip(df_names['change_type_flag'], df_names['name'])) #O(N)
        for index,name in enumerate(df['name']): #O(m) number of rows in df, O(M*N*K) k is time complexity of token sort ratio
            df.loc[index, "change_type"] = 4
            LLM_needed = True
            match = process.extract(str(name), temp_dict, processor=default_process,scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
                                                                # removing all non alphanumeric characters
                                                                # trimming whitespaces
                                                                # converting all characters to lower case
            match = sorted(match, key=lambda x: x[1])
            if match:
                for name, score, changetype in match:
                    changetype = changetype.split("$$$$")[0]
                    if score >= 100:
                        try:
                            df.loc[index, "change_type"] = int(changetype)
                        except:
                            logger.error(f"could not convert changetype to int for name:{name}, score:{score}, change_type:{changetype}") #todo review
                            df.loc[index, "change_type"] = 4
                        LLM_needed = False
                        break
                    df.loc[index, "change_type"] = f"""(name: {name}, score: {str(score)}, changetype: {changetype}) \n {str(df.loc[index, "change_type"])}"""
            if LLM_needed:
                input1 = str(name)
                input2 = str(df.loc[index, "change_type"])
                prompt_inputs_changetype = f"""input1: {input1}\ninput2: {input2}"""
                message = retry_llm_calls_with_constant_delay(get_messages(prompt_inputs_changetype, eu_prompts.system_prompt_fuzzy_changeType))
                response = get_text_from_llm_response(message)
                if response:
                    try:
                        response = json.loads(response)
                        change_Type_from_llm = response.get("changeType")
                        change_Type_from_llm = int(change_Type_from_llm)
                        df.loc[index, "change_type"] = changetype
                    except Exception as E:
                        logger.error(f"Error while getting changeType for names without name match; name: {name}, response_LLM:{response}")
                        change_Type_from_llm = 4
                else:
                    logger.info(f"Did not get any response from the LLM for names without name match; name: {name}")
                    change_Type_from_llm = 4
                df.loc[index, "change_type"] = change_Type_from_llm
            df = df.reset_index(drop=True)
        return df
    except Exception as E:
        raise Exception(f"Error in fuzzy_merge_names as: {E}")


def add_leading_zeros_str(num_str):
    # Ensure the input is a valid number string
    if not num_str.isdigit():
        return f"Invalid docnum. {num_str}"
    if len(num_str) > 4:
        return(f"The docnum string is of length: {len(num_str)}")
    # Add leading zeros to make the string 4 digits long
    return num_str.zfill(4)

def is_latin(char):
    return 'LATIN' in unicodedata.name(char, '')

def get_all_punctuation_and_separators():
    list_of_symbols = ["-","–","'"," ","”","“","/","&","(",")","","1","2","3","4","5","6","7","8","9","0", "’", ".","‘",","]
    symbols = set(list_of_symbols) 
    for character in range(0x110000):
        char = chr(character)
        category = unicodedata.category(char)
        if category.startswith(("P", "Z")): 
            symbols.add(char)
    return list(symbols)

list_of_symbols_names_can_have = get_all_punctuation_and_separators()
list_of_string_identifiers = ["'","”","“","’","‘"]