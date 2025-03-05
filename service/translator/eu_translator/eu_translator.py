import utils.eu_utils.eu_common_utils as eu_common_utils
import utils.eu_utils.eu_post_process_utils as eu_post_process_utils
from utils.eu_utils.eu_modify_output_before_s3_utils import sort_in_alphabetic, filter_additions_amendments, filter_unacceptable_entity_type
from bson import ObjectId
from datetime import datetime
from datetime import timezone
from service.logger.logger import get_logger
logger = get_logger("eu_translator")

from service.database.database_service import entity_collection, pr_collection

def translator(pr, result_list_of_json_unsorted):
    keys = []
    errors = []
    result = []
    if not isinstance(result_list_of_json_unsorted, list):
        logger.error(f"result list of json not a list: {result_list_of_json_unsorted}")
        raise Exception(f"result list of json not a list: {result_list_of_json_unsorted}")
    result_list_of_json_unsorted = filter_unacceptable_entity_type(result_list_of_json_unsorted)
    number_title, listentryidfirsthalf = eu_common_utils.get_numbertit_and_listentry(pr)
    result_list_of_json_sorted = sort_in_alphabetic(result_list_of_json_unsorted)
    prExtractionTimestamp = datetime.now(timezone.utc).isoformat(' ', 'seconds')
    for index in range (0, len(result_list_of_json_sorted)):
        data = result_list_of_json_sorted[index] # thus temp variable has to be in a dict format necessarily
        entity = cdf_conversions(data,number_title,listentryidfirsthalf,index, pr, prExtractionTimestamp)
        if entity:
            keys.append(entity.get("_id"))
            
            entity_collection.insert_one(entity)

            result.append(entity)
        
    logger.info("error %s",errors)
    logger.info("keys %s", keys)
    pr = eu_common_utils.update_pr(pr)
    pr_collection.update_one({"pressReleaseUrl": pr.get("pressReleaseUrl"), "listId": pr.get("listId")}, {"$set": pr})
    result_filtered = filter_additions_amendments(result)
    return result_filtered, errors

def perform_basic_checks(data):
    entityTypeName =  data.get("entityType") if data.get("entityType") not in eu_common_utils.not_expected_outcomes else None
    if entityTypeName in eu_common_utils.not_expected_outcomes:
        raise Exception("No entity Type found")
    primaryname = data.get("name")
    if primaryname in eu_common_utils.not_expected_outcomes:
        logger.error(f"PRIMARY NAME IN NOT EXPECTED OUTCOME or None: {primaryname}")
        raise Exception(f"PRIMARY NAME IN NOT EXPECTED OUTCOME or None: {primaryname}")
    if entityTypeName in ["individual", "Individual", "Person","person"]:
        entityTypeName = "person"
    else:
        entityTypeName = "enterprise"
    primaryname = eu_post_process_utils.remove_identifiers_from_string(primaryname)
    return primaryname, entityTypeName
        
def cdf_conversions(data,number_title,listentryidfirsthalf,index, pr, prExtractionTimestamp):
    try:
        listentryid = str(listentryidfirsthalf)+str(eu_common_utils.add_leading_zeros_str(str(index+1)))
        key = str(ObjectId())
        primaryname, entityTypeName = perform_basic_checks(data)
        all_cases = ["ALL", "All", "all"]
        if primaryname in all_cases:
            return None
        entity = {
            "_id":key,
            "listEntryId":listentryid,
            "sourceNaturalKey": listentryid,
            "entityTypeName": entityTypeName,
            "nameDetailsList": eu_post_process_utils.process_names(data, entityTypeName, primaryname),
            "titles": eu_post_process_utils.process_titles(data.get("designation")), 
            "birthDateDetailsList":eu_post_process_utils.convert_string_of_arr_to_key_value_pairs(
                eu_common_utils.convert_to_ddmmyyyy_format(data.get("dateOfBirth")), 
                "date"
                ),
            "birthPlaceDetailsList":eu_post_process_utils.convert_string_of_arr_to_key_value_pairs(data.get("placeOfBirth"), "place"),
            "nationalityDetailsList":eu_post_process_utils.process_nationality(data.get("nationality_Country_Name")),
            "citizenshipDetailsList":eu_post_process_utils.convert_string_of_arr_to_key_value_pairs(data.get("citizenship_Country_Name"),"countryName"),
            "gender":eu_post_process_utils.process_gender(data.get("gender")),
            "idNumberTypesList": eu_post_process_utils.process_id_details(data),
            "addressDetailsList":eu_post_process_utils.process_address(data.get("addressDetails"), data.get("placeofRegistration")),
            "listingDateTime":eu_post_process_utils.process_listed_on(data.get("listedOn")), 
            "contactList": eu_post_process_utils.process_contact_info(data),
            "regulationsList": [
                {"numberTitle": str(number_title),
                "publicationUrl": pr.get("pressReleaseUrl"),
                "entryIntoForceDate": pr.get("pressReleaseDateTime")}
            ],
            "firstMiddleLastNameLists": str(data.get("name_alias_info")) if data.get("name_alias_info") not in eu_common_utils.exempt_from_mongo else None,
            "ogScriptNamesList": str(data.get("originalScriptName")) if data.get("originalScriptName") not in eu_common_utils.exempt_from_mongo else None, 
            "complete_name_related_information": str(data.get("name_info")),
            # "imageInfo":data.get("imageNumbers"),
            "primaryName":primaryname,
            "sourceActionId":data.get("change_type"),
            "actionId":int(1),
            "additionalInformation":data.get("completeInformation") if data.get("completeInformation") != "" else None,
            "addedDateTime": datetime.now(timezone.utc).isoformat(' ', 'seconds'),
            "prExtractionDateTime":prExtractionTimestamp,
            "prDownloadedDateTime":pr.get("scrapedDateTime"),
            "prIdentifiedDateTime":pr.get("addedDateTime"),
            "addedUserId": "EU_PRESS_LLM_EXTRACTOR",
            "listId": "79",
            "listName": "EU-PR",
        }
        entity = {k: v for k, v in entity.items() if v not in eu_common_utils.exempt_from_mongo}
        entity = eu_post_process_utils.process_entity_for_names_and_titles(entity, entityTypeName)
        return entity
    except Exception as E:
        logger.error(f"error in cdf conversion for entity: {data}, error: {E}")
        return None