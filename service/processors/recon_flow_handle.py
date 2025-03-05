from config.config import Config

from service.database.database_service import entity_collection,pr_collection
from service.logger.logger import get_logger

from utils.eu_utils.eu_url_parser_utils import get_title

from datetime import datetime
from datetime import timezone
from bson import ObjectId
logger = get_logger(__name__)


def should_proceed_with_rt_extraction (pr):
    if entity_collection.find_one({"regulationsList.numberTitle": pr.get("numberTitle"), "listId":str(Config.LIST_ID)}):
        return False
    return True

def should_make_entry_in_pr_collection(translatted_entities):
    number_title = translatted_entities[0].get("regulationsList",[{}])[0].get("numberTitle",None)
    if pr_collection.find_one({"numberTitle": number_title, "listId":int(Config.LIST_ID)}):
        return False
    return True

def make_entry_in_pr_collection(translatted_entities):
    try:
        press_release_url = translatted_entities[0].get("regulationsList",[{}])[0].get("publicationUrl",None)
        try:
            title = get_title(press_release_url)
        except Exception as E:
            logger.error(E)
            title = f"COULD NOT GET TITLE FOR THE URL: {press_release_url}"
        data= {
                    "_id": str(ObjectId()),
                    "pressReleaseTitle": title, #we donot get this can be scrapped from the URL if required
                    "pressReleaseUrl": press_release_url,
                    "guid": press_release_url.split(":")[-1] if press_release_url else None,
                    "pressReleaseUrlAccess":press_release_url,
                    "numberTitle":translatted_entities[0].get("regulationsList",[{}])[0].get("numberTitle",None),
                    "listEntryIdFirstHalf": translatted_entities[0].get("listEntryId", "")[:-4] if translatted_entities[0].get("listEntryId") else "",
                    "pressReleaseDateTime": translatted_entities[0].get("regulationsList",[{}])[0].get("entryIntoForceDate",None), 
                    "addedDateTime": datetime.now(timezone.utc).isoformat(' ', 'seconds'),
                    "addedUserId": "HITL",
                    "scrapedDateTime": translatted_entities[0].get("prDownloadedDateTime",None),
                    "scrapedUserId": "HITL",
                    "isChecked": False,
                    "isExtracted": True,
                    "listId": int(Config.LIST_ID),
                    "listName": "EU-PR", 
                    "status": "HITL_BACKFILL_INITIATED",
                    "error": None,
                    "errorCount":0,
                    "failed" : False,
                    "should_retry":False,
                    "retry_count_for_html_availibility":0,
                    "identifiedDateTime": translatted_entities[0].get("prIdentifiedDateTime",None),
                    "identifiedUserId": "HITL",
                    "isSanctionDetected": True,
                    "extractedDateTime": translatted_entities[0].get("prExtractionDateTime",None),
                    "extractedUserId": "HITL"
        }
        pr_collection.insert_one(data)
        logger.info(f"PR collection inserted into collection, url: {press_release_url}")
    except Exception as E:
        logger.error(f"Error in make entry in pr collection after HITL Backfill Inititated, with exception {E} and {translatted_entities[0]}")
        raise Exception(f"Error in make entry in pr collection after HITL Backfill Inititated, with exception {E} and {translatted_entities[0]}")