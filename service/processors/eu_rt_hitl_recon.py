from service.s3.s3_service import upload_to_s3,get_file_from_s3
from service.logger.logger import get_logger
from service.database.database_service import entity_collection
from config.config import Config
import json

logger = get_logger(__name__)

def hitl_rt_recon():
    try:
        # this methods does a on fly reconcilication of RT and HITL feed 
        #  Triggered on: HITL list ingestion 
        filepath =  Config.RECON_FILE_PATH
        logger.info(f"Performing recon of RT with HITL file {filepath}")
        if not filepath:
            raise Exception("filepath is none or empty: existing") 
        data = get_file_from_s3(Config.S3_BUCKET,filepath)
        data = json.loads(data)
        logger.info(f"Data from HITL feed {data} ")
        missed_records = []
        for entity in data:
            listEntryId = entity.get("listEntryId")
            present = entity_collection.find_one({"listEntryId":listEntryId,"listId":"79"})
            if(not present):
                # means that it was missed in RT field
                logger.info(f"{listEntryId} listEntryId was missed in the RT feed")
                # change the list id remove _id ane insert to RT PressEntity collection 
                entity = transform_to_rt(entity)
                entity_collection.insert_one(entity)
                missed_records.append(entity)
        logger.info(f"Total {len(missed_records)} records are missed in the RT feed, proceeding with reconciliation")
        # read file from s3
        return missed_records
    except Exception as e:
        raise Exception(f"Error in recon {e}")

def transform_to_rt(entity):
    entity.pop("_id",None)
    entity['listId'] = "79"
    entity['listName'] = "EU-PR"
    entity['sourceActionId'] = int(entity['sourceActionId'])
    entity['actionId'] = int(entity['actionId'])
    entity['addedUserId'] = 'HITL-RT-RECON-JOB'
    return entity