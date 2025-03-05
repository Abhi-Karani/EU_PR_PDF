import utils.eu_utils.eu_common_utils as eu_common_utils
import json
import pandas as pd
from service.logger.logger import get_logger
import ast
logger = get_logger("eu_post_process_utils")

def remove_identifiers_from_string(input_string, identifiers=eu_common_utils.list_of_string_identifiers):
    if input_string and input_string[0] in identifiers and input_string[-1] in identifiers:
        return input_string[1:-1]
    return input_string

def itterate_aliases_og(arr, nameType, nameDetails):
    try:
        if isinstance(arr, str):
            arr = eu_common_utils.input_string_array_output_array(arr)
        if not arr:
            return nameDetails
        if isinstance(arr, list):
            for name in arr:
                if name:
                    new_name = eu_common_utils.replace_image_from_string(name)
                    new_name = remove_identifiers_from_string(new_name)
                    if new_name:
                        detail = {
                            "nameType":nameType, 
                            "fullName":new_name
                        }
                        nameDetails.append(detail)
        else:
            logger.info(f"input to itterate_aliases_og is not a list: {arr}")
        return nameDetails
    except Exception as E:
        logger.error(f"Error in itterate_aliases_og")
        raise Exception(f"Error in itterate_aliases_og")

def process_names(data, entityTypeName, primaryname):
    nameDetails = []
    try:
        if entityTypeName in eu_common_utils.acceptable_values_for_individual:
            first_name, last_name = extract_first_and_last_name(primaryname)
        else:
            first_name = ""
            last_name = primaryname 
        details = {
            "nameType":"Primary Name",
            "fullName":primaryname,
            "firstName":first_name,
            "lastName":last_name
        }
        nameDetails.append(details)
        key_latin = ["aliases"]
        for i in key_latin:
            arr = data.get(i)
            nameDetails = itterate_aliases_og(arr, "Aliases", nameDetails)

        key_non_latin = ["aliases_og"]
        for i in key_non_latin:
            arr = data.get(i)
            nameDetails = itterate_aliases_og(arr,"Original Script Name",nameDetails)
        return nameDetails
    except Exception as E:
        logger.error(f"Error in process_names: {E} for data: {data}")
        return nameDetails

def extract_first_and_last_name(name):
    try:
        if name in eu_common_utils.not_expected_outcomes or not isinstance(name, str):
            return "", name
        
        # Split the name based on spaces
        name_parts = name.strip().split() #ADD maybe can add isinstance list walla 

        # If there's only one name, return it as the last name
        if len(name_parts) == 1:
            return '', name_parts[0]  # First name is empty, last name is the only name
        
        # The first name is everything before the last space, and the last name is the final part
        first_name = ' '.join(name_parts[:-1])  # Join everything except the last part
        first_name,_ = extract_name_and_title(first_name)
        last_name = name_parts[-1]  # The last part of the split
        return first_name, last_name
    except Exception as E:
        logger.error(f"Error in extract_first_and_last_name for name: {name} and error: {E}")
        return "", name

def extract_name_and_title(input_string):
    if input_string in eu_common_utils.not_expected_outcomes:
        logger.info(f"in extract_name_and_title, input is {input_string} in not_expected_outcomes")
        return None, None
    try:
        matched_titles = []  
        for string in eu_common_utils.common_titles:
            if string in input_string:  # Check if the string is in the input
                matched_titles.append(string)  
        if matched_titles:
            # Sort titles by length to ensure longest match is used first
            matched_titles = sorted(matched_titles, key=len, reverse=True)
            input_string = input_string.replace(matched_titles[0], "")  # Remove title from input

        input_string = input_string.lstrip(' ,.-')
        if not input_string:
            return None, None
        return input_string.strip(), matched_titles[0] if matched_titles else None
    except Exception as E:
        logger.error(f"Error in extract_name_and_title for input:{input_string} and error: {E}")
        return input_string.strip(), None
    
def process_titles(title_info):
    title_list = []
    try:
        if title_info in eu_common_utils.not_expected_outcomes:
            return None
        if isinstance(title_info, str):
            temp_list_titles = eu_common_utils.input_string_array_output_array(title_info)
            if temp_list_titles:
                title_list = temp_list_titles
        elif isinstance(title_info, list):
            title_list = title_info
        else: 
            logger.info(f"input in process_titles is neither string nor list {title_info}")
            return None
        new_title_list = eu_common_utils.remove_image_from_each_string_in_a_list_of_string(title_list)
        return new_title_list
    except Exception as E:
        logger.error(f"Error in process_titles, {title_info} E: {E}")
        return title_list

def convert_string_of_arr_to_key_value_pairs(string_array, key):
    if string_array in eu_common_utils.not_expected_outcomes:
        return None
    else:
        list_of_key_val_dicts = []
        try:
            if isinstance(string_array,str):
                strs = eu_common_utils.input_string_array_output_array(string_array)
                if strs:
                    if not isinstance(strs, list):  #this condition will never be true
                        dictionary = {key: str(strs)}
                        list_of_key_val_dicts.append(dictionary)
                    else:
                        for i in strs:
                            new_i = eu_common_utils.replace_image_from_string(str(i))
                            if new_i:
                                dictionary = {key: new_i}
                            list_of_key_val_dicts.append(dictionary)
            elif isinstance(string_array, list):
                for i in string_array:
                    new_i = eu_common_utils.replace_image_from_string(str(i))
                    if new_i:
                        dictionary = {key: new_i}
                    list_of_key_val_dicts.append(dictionary)
            else:
                logger.info(f"The input in convert_string_of_arr_to_key_value_pairs is neither list nor str: {string_array}")
                return None
            return list_of_key_val_dicts
        except Exception as E:
            logger.error(f"Error in convert_string_of_arr_to_key_value_pairs, {string_array} and key:{key} E: {E}")
            return list_of_key_val_dicts
def convert_nationality_into_country(nationality):
    try:
        for _,adjectivals in eu_common_utils.country_nationality_df.iterrows():
            if nationality in adjectivals.values:
                return adjectivals.iloc[0]
    except Exception as E:
        logger.error(f"Error in convert_nationality_into_country, {nationality} and Error: {E}")
    return nationality

def process_nationality(string_array):
    if string_array in eu_common_utils.not_expected_outcomes:
        return None   
    list_of_dictionary_nationality = convert_string_of_arr_to_key_value_pairs(string_array,"countryName")
    if not list_of_dictionary_nationality:
        return None
    try:
        for nationality_dictionary in list_of_dictionary_nationality:
            nationality = nationality_dictionary["countryName"]
            country = convert_nationality_into_country(nationality)
            nationality_dictionary["countryName"] = country
    except Exception as E:
        logger.error(f"Error in process_nationality for input {string_array} and Error: {E}")
    return list_of_dictionary_nationality

def process_gender(gender_details):
    gender = ""
    try:
        if gender_details in eu_common_utils.not_expected_outcomes:
            return None
        if isinstance(gender_details,str):
            gender_details_list = eu_common_utils.input_string_array_output_array(gender_details)
            if gender_details_list:
                gender = gender_details_list[0]
        if isinstance(gender_details, list):
            gender = gender_details[0]

        if gender and isinstance(gender,str):
            return gender
        logger.info(f"input in process_gender is neither list not string, {gender_details}")
        return None
    except Exception as e:
        logger.error(f"Error in function process_gender {gender_details}, error: {e}")
        return None

def process_id_details(data):
    idDetails = []
    try:
        list_of_dicts_string = data.get("idDetails")
        if list_of_dicts_string in eu_common_utils.not_expected_outcomes:
            return None
        if list_of_dicts_string:
            list_of_dicts_string = list_of_dicts_string.replace("None", "'NA'")
            list_of_dicts = json.loads(list_of_dicts_string.replace("'", '"'))
            if not isinstance(list_of_dicts, list):
                return []
            if list_of_dicts:
                for dictionary in list_of_dicts:
                    if isinstance(dictionary,dict):
                        value_old = dictionary.get("idValue")
                        if isinstance(value_old, str):
                            value_new = eu_common_utils.replace_image_from_string(str(value_old))
                        else:
                            logger.info(f"id value is not a string, {value_old}")
                            value_new = None
                        if value_new:
                            id_type = dictionary.get("idType")
                            id_remarks = dictionary.get("id_remarks")
                            if id_remarks in eu_common_utils.unacceptable_id_remarks:
                                remark_value_for_id_in_db = f"{id_type}"
                            else:
                                remark_value_for_id_in_db = f"{id_type}, {id_remarks}"
                            id_detail = {
                                "idType":get_id_category(id_type),
                                "idValue": value_new,
                                "remarks":remark_value_for_id_in_db
                            }
                            idDetails.append(id_detail)                    
        return idDetails
    except Exception as e:
        logger.info(f"Error in function process_id_details for {data}, error: {e}")
        return None

def get_id_category(idtype):
    try:
        for category in eu_common_utils.id_mapping_excel_df.columns:
            if idtype.lower().strip() in eu_common_utils.id_mapping_excel_df[category].str.lower().dropna().values:
                return category
    except Exception as e:
        logger.error(f"Error in get_id_category {e} for idType: {idtype}")
    return 'other'
 
def process_address(string_array, place_of_reg):
    list_of_key_val_dicts = []
    try:
        if place_of_reg not in eu_common_utils.not_expected_outcomes and isinstance(place_of_reg, str):
            country_name = get_country_names(place_of_reg)
            dictionary = {
                    "addressType": "Place of Registration",
                    "addressLine1": place_of_reg,
                    "countryName":str(country_name)
                }
            list_of_key_val_dicts.append(dictionary)
        if not string_array in eu_common_utils.not_expected_outcomes:
            if isinstance(string_array, str): 
                addresses_list = eu_common_utils.input_string_array_output_array(string_array)
            elif isinstance(string_array, list):
                addresses_list = string_array
            else:
                logger.info(f"input in process_address neither list nor string: {string_array}")
                return None
            addressType = "default"
            if addresses_list:
                if not isinstance(addresses_list,list):
                    return None
                for i in addresses_list:
                    if i in eu_common_utils.not_expected_outcomes or not isinstance(i, str):
                        logger.info(f"address: {i} is in not expected outcomes or is not a string")
                        continue
                    new_i = eu_common_utils.replace_image_from_string(i)
                    if not new_i:
                        continue
                    country_name = get_country_names(new_i)
                    dictionary = {
                        "addressType": addressType,
                        "addressLine1": new_i,
                        "countryName":str(country_name)
                    }                        
                    list_of_key_val_dicts.append(dictionary)
                    addressType = "alternate address"
        return list_of_key_val_dicts
    except Exception as E:
        logger.error(f"error in process_address input: {string_array},place of reg {place_of_reg}, error: {E}")
        return list_of_key_val_dicts
    
def get_country_names(input_string):
    try:
        if not input_string:
            return " "
        for country in eu_common_utils.country_names_list:
            if country.lower() in input_string.lower():
                return country
        return " "
    except Exception as E:
        logger.error(f"error in get_country_names input: {input_string}, error: {E}")

def process_listed_on(listed_on_info):
    date_in_consideration = get_date_in_consideration(listed_on_info)
    if not date_in_consideration:
        return None
    try:
        if isinstance(date_in_consideration, str):
            date = eu_common_utils.convert_to_ddmmyyyy_format(date_in_consideration)
            if date:
                if isinstance(date, list):
                    final_date = str(date[0])
                elif isinstance(date, str):
                    date_arr = eu_common_utils.input_string_array_output_array(date)
                    if date_arr:
                        final_date = str(date_arr[0])
                else:
                    logger.info(f"formatted date for listed-on-info is neither str nor list, {date}")
                    return None
            else:
                return None
        final_date_new = eu_common_utils.replace_image_from_string(final_date)
        return final_date_new
    except Exception as E:
        logger.error(f"Error in process_Listed_on whilst converting to ddmmyyyformat for date_in_consideration:{date_in_consideration}, {E}")
        return None

def get_date_in_consideration(listed_on_info):
    date_in_consideration = ""
    try:
        if listed_on_info in eu_common_utils.not_expected_outcomes:
            return None
        if isinstance(listed_on_info,list):
            date_in_consideration = str(listed_on_info[0])
        elif isinstance(listed_on_info,str):
            array_of_dates = eu_common_utils.input_string_array_output_array(listed_on_info)
            date_in_consideration = str(array_of_dates[0])
        else:
            logger.info(f"listed-on-info is neither list nor string: {listed_on_info}")
            return None
        return date_in_consideration
    except Exception as E:
        logger.error(f"Error in process_Listed_on whilst trying to get date_in_consideration, input: {listed_on_info}, error: {E}")
        return None
    
def process_contact_info(data):
    contact_values = []
    try:
        values = data.get("contactInformation") 
        if values in eu_common_utils.not_expected_outcomes:
            return None
        if isinstance(values, str):
            values = eu_common_utils.input_string_array_output_array(values)
        if values:
            if isinstance(values, list):
                for val in values:
                    if val and val not in eu_common_utils.not_expected_outcomes:
                        if isinstance(val, str):
                            new_val = eu_common_utils.replace_image_from_string(val)
                            if new_val:
                                contact_values.append(new_val)
            else:
                logger.info(f"contactInfo is not a list: {values}")
        else:
            return None
        return contact_values
    except Exception as E:
        logger.error(f"error in process_contact_info input: {data}, error: {E}")
        return contact_values
    
def process_entity_for_names_and_titles(entity, entityTypeName):
    try:
        if entityTypeName in eu_common_utils.acceptable_values_for_individual :
            matched_title = []
            titles = entity.get("titles", [])  # Initialize or get existing titles
            primaryName = entity.get("primaryName")
            try:
                valid_name_primary, matched_title_primary = extract_name_and_title(primaryName)
                if matched_title_primary:
                    entity["primaryName"] = valid_name_primary.strip()
                    titles.append(matched_title_primary)
            except Exception as e:
                    logger.error(f"Error processing primary Name, {primaryName}, error: {e}")

            nameDetailsList = entity.get("nameDetailsList")
            for name_detail in nameDetailsList:
                try:
                    valid_name, matched_title = extract_name_and_title(name_detail.get("fullName", ""))
                    if matched_title:
                        name_detail["fullName"] = valid_name.strip()  # Update with the extracted valid name, python dictionaries and lists are mutable
                        titles.append(matched_title)  # Append matched title to titles list
                except Exception as e:
                    logger.error(f"Error processing name for, {name_detail}, error: {e}")
            try:     
                name_alias_info = ast.literal_eval(entity.get("firstMiddleLastNameLists", "{}"))
                titles.extend(name_alias_info.get("titles", []))
            except Exception as E:
                logger.error(f"error in adding titles from response 2 call")
            if titles:
                titles = list(set(titles))
                entity["titles"] = titles  # Update entity with titles
        return entity
    except Exception as E:
        logger.error(f"Error in process_entity_for_names_and_titles for {entity}, error:{E}")
        return entity