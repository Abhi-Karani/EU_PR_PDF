import utils.eu_utils.eu_common_utils as eu_common_utils
from service.logger.logger import get_logger
logger = get_logger("eu_modify_output_before_s3")

def sort_in_alphabetic(result_list_of_json_unsorted):
    valid_records = []
    for entry in result_list_of_json_unsorted:
        try:
            # Validate if 'primaryKey' exists and can be sorted
            _ = entry['name']  # Accessing key to ensure no KeyError
            valid_records.append(entry)  # Add valid items to the list
        except Exception as E:
            logger.error(f"error in sort_in_alphabetic, entry: {entry} and error: {E}")
            continue
    try:
        sorted_data = sorted(valid_records, key=lambda item: item['name'].lower())
        return sorted_data
    except Exception as E:
        logger.error(f"error in sort_in_alphabetic in sorting, error: {E}")
    return result_list_of_json_unsorted

def filter_additions_amendments(result):
    result_additions_amendments = []
    for entity in result:
        if int(entity["sourceActionId"])==int(3):
            logger.info(f"{entity} is removed from json that is supposed to be dumped to S3") #todo notify the analyst to check
        else:
            result_additions_amendments.append(entity)
    return result_additions_amendments

def filter_unacceptable_entity_type(result_list_of_json_unsorted):
    valid_records = []
    for entry in result_list_of_json_unsorted:
        try:
            # Validate if 'primaryKey' exists and can be sorted
            entity_type = entry['entityType'].lower()  # Accessing key to ensure no KeyError
            if entity_type not in eu_common_utils.unacceptable_entityTypes:
                valid_records.append(entry)  # Add valid items to the list
        except Exception as E:
            logger.error(f"error in filter_unacceptable_entity_type, entry: {entry} and error: {E}") #todo send notification
            continue
    return valid_records