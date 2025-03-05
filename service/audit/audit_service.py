
from service.database.database_service import monitor_details_collection
from datetime import datetime, timezone
from service.logger.logger import get_logger
logger = get_logger("audit_service")


def add_audit(guid, run_id, list_id, list_name, rss_url, filepath, filesize, checksum):
    try:
 
        monitor_details_data = {}
        monitor_details_data["guid"]= guid
        monitor_details_data["run_id"]= run_id
        monitor_details_data["listId"]= int(list_id)
        monitor_details_data["listName"]= list_name
        monitor_details_data["addedDateTime"]= datetime.now(timezone.utc)
        monitor_details_data["monitorUrlText"]= rss_url
        monitor_details_data["fileSize"]= filesize
        monitor_details_data["checksumValue"]= checksum
        monitor_details_data["filePathText"]= filepath
        monitor_details_data["__v"]= 0
        monitor_details_collection.insert_one(monitor_details_data)
        logger.info("Updated the audit in prMonitorDetails")
    except:
        logger.error("Not able to update monitor status in mongo")
        raise Exception("Not able to update monitor status in mongo")