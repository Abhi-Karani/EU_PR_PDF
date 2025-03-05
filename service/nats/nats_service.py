from config.config import Config
from datetime import datetime,timezone
import hashlib,os,sys
import nats
import json
import asyncio
from service.logger.logger import get_logger
logger = get_logger("nats_service")


async def write_to_nats(subject, data):
    try:
        logger.info("Sending event to NATS server")
        nats_server = Config.NATS_SERVER
        nats_username = Config.NATS_USERNAME
        nats_password = Config.NATS_PASSWORD
        async def error_cb(e):
            logger.info("Error: %s", e)
            
        async def reconnected_cb():
            logger.info("Got reconnected to NATS...")
            
        logger.info("publishing to %s",nats_server)
        
        if not nats_username or not nats_password:
            logger.info("NATS_USERNAME and NATS_PASSWORD not available")
    
        nc = await nats.connect(servers = [nats_server],
                                user = nats_username,
                                password= nats_password,
                                error_cb= error_cb,
                                reconnected_cb= reconnected_cb,
                                connect_timeout=30,
                                max_reconnect_attempts=3)
    
        # Create JetStream context.
        
        js = nc.jetstream()
        nats_pub_data = {} 
        metadata = {}
        metadata["publisher"] = "Press Release Extractor System"
        metadata["type"]= "Event-PUSH"
        metadata["timestamp"]= datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        nats_pub_data["data"] = json.dumps(data)
        nats_pub_data["metadata"] = metadata 
        data = json.dumps(nats_pub_data)
        await js.publish(subject, data.encode())
        logger.info("Successfully send event to subject %s",subject)
        return data
    except Exception as e:
        logger.error("Error while publishing event to nats %s",e)
        raise e


def publish(subject,event):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(write_to_nats(subject,event))
    return event


def get_file_hash(data):
    try:
        data = json.dumps(data,default=str, sort_keys=True, indent=2)
        checksum = hashlib.md5(data.encode("utf-8")).hexdigest()
        return checksum
    except Exception as e:
        print("Error while getting checksum of the file content")
        raise e


def get_data_to_publish(data_in_s3, filepath, source_list_type_id, source_list_id, list_name, rss_link):
    data = {}
    data['listTypeId'] = source_list_type_id
    data['listId']=source_list_id
    data['listName']= list_name
    data['lastCheckedDateTime']=  datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    details = {}
    details["lastModifiedDateTime"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    details["fileSize"] = sys.getsizeof(data_in_s3)
    details["checksumValue"] = get_file_hash(data_in_s3)
    details["fileDownloadedDateTime"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    details["sourceUrl"] = rss_link
    details["filePath"] = filepath
    data["details"] = details
    return data