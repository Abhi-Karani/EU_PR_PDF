from config.config import Config
from service.base.BaseService import BaseService
from service.extractor.eu_extractor.eu_extractor import extractor
from service.translator.eu_translator.eu_translator import translator
from service.success_email.success_email_service import send_success_notification
import utils.eu_utils.eu_common_utils as eu_common_utils
from service.database.database_service import pr_collection
from service.s3.s3_service import get_file_from_s3, upload_to_s3
from service.nats.nats_service import publish, get_data_to_publish
from service.error_email.error_email_service import send_error_email
from service.audit.audit_service import add_audit
from bson import ObjectId
from bs4 import BeautifulSoup
from service.logger.logger import get_logger
from service.processors.eu_rt_hitl_recon import hitl_rt_recon as eu_hitl_rt_recon
from service.processors.recon_flow_handle import should_proceed_with_rt_extraction, should_make_entry_in_pr_collection, make_entry_in_pr_collection
from datetime import datetime
logger = get_logger("EUService")

class EUService(BaseService):
    
    def __init__(self):
        
        logger.info("Starting EU Service")
        
        # HARDCODED LIST ID
        self._LIST_TYPE_ID = "6"
        self._LIST_ID = "79"
        self._LIST_RSS_LINK = "https://eur-lex.europa.eu/EN/display-feed.rss?myRssId=zqe4%2F5c25EYwdPmi2HNYOslKT%2Bjqe67%2B34BQc2GHacM%3D"

        # get S3 bucket name from env
        self._s3_bucket = Config.S3_BUCKET
        self._s3_path_recon = f"source_raw_files/EU-PR/snap/recon"
        self._html_file_name = "raw.html"
        self._result_file_name = "result.json"
        self._recon_file_suffix = "_recon.json"

        if(Config.RECON_MODE != "true" ):
             # TODO: GUID
            # get GUID of current PR from env
            self._guid = Config.GUID  # Default to None if not set
            # get RUN ID of current PR from env
            self._run_id = Config.RUN_ID
            logger.info(f"Run id: {self._run_id}")
            self._s3_path_pr = f"source_raw_files/EU-PR/snap/{Config.GUID}"
            # Get HTML from S3 and load as soup
            self._full_content_html =  BeautifulSoup(get_file_from_s3(self._s3_bucket, f"{self._s3_path_pr}/{self._html_file_name}"), 'html.parser')
            logger.info(f"loaded HTML : {self._full_content_html}")
            self._press_release_record = pr_collection.find_one({'_id': self._run_id})
            logger.info("Press Release %s", self._press_release_record)
        
        
        logger.info(f"EU Service initialised with List ID: {self._LIST_ID}")
   
    def extractor(self, press_release_record, full_content_html):
        return extractor(press_release_record, full_content_html);

    def translator(self, pr, entities):
        return translator(pr, entities)

    def upload_to_s3(self, s3_bucket, s3_path, file_name, data):
        return upload_to_s3(s3_bucket, s3_path, file_name, data)
    
    def success_notification(self, pr, entities, errors):
        return send_success_notification(pr, entities, errors)
    
    def error_notification(self, list_name, error):
        send_error_email(list_name, error)
   
    def notify_via_nats(self, subject, data):
        return publish(subject, data)
    
    def audit(self, guid, run_id, list_id, list_name, rss_url, filepath, filesize, checksum):
        add_audit(guid, run_id, list_id, list_name, rss_url, filepath, filesize, checksum)
    
    def recon_with_hitl(self):
        try:
            recon_entities = eu_hitl_rt_recon()
            return recon_entities
        except Exception as e:
            self.error_notification("EU", error="ERROR in HITL Recon")
            logger.info("Error email sent and PR entry updated with error")
    def run(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        errors = []
        try:
            if(Config.RECON_MODE == "true" ):
                logger.info("Running in recon mode")
                translated_entities = self.recon_with_hitl()
                filename =  timestamp+self._recon_file_suffix
                if(not len(translated_entities)):
                    logger.info("no missed entities; nothing to reconcile")
                    return
                if should_make_entry_in_pr_collection(translated_entities):
                    logger.info("No PR found in collection, making an entry")
                    make_entry_in_pr_collection(translated_entities)
                s3_link = self.upload_to_s3(self._s3_bucket, self._s3_path_recon , filename, translated_entities)
                self._guid = timestamp
                self._run_id = timestamp
                self._press_release_record = translated_entities[0] 
                
            else:
                if not should_proceed_with_rt_extraction(self._press_release_record):
                    raise Exception("Records for this PR already ingested, hence not proceeding with extraction")
                entities = self.extractor(self._press_release_record, self._full_content_html)
                # logger.info("Raw Entities extracted from LLM: %s", entities)
                filename = self._result_file_name
                # Translate to CDF and dump in mongo
                translated_entities, errors = self.translator(self._press_release_record, entities)
                # logger.info("Translated entities : %s", translated_entities)
                logger.info("Errors in translations : %s", errors)
                if(not len(translated_entities)):
                    logger.info("no entities extracted")
                    raise Exception(f"""No entities extracted for the URL""")
                    # return
                s3_link = self.upload_to_s3(self._s3_bucket, self._s3_path_pr , filename, translated_entities)
            
            if(Config.TEST_RUN == "false" ):
                # Send NATS event            
                puslished_data = self.notify_via_nats(Config.NATS_EU_SUBJECT, get_data_to_publish(translated_entities,s3_link, self._LIST_TYPE_ID, self._LIST_ID, "EU-PR", self._LIST_RSS_LINK))
                
                
                # Add audit
                self.audit(self._guid, self._run_id, puslished_data.get("listId"), puslished_data.get("listName"), puslished_data.get("details").get("sourceUrl"), puslished_data.get("details").get("filePath"), puslished_data.get("details").get("fileSize"), puslished_data.get("details").get("checksumValue"))
                
                # Send success email 
                self.success_notification(self._press_release_record, translated_entities, errors)
            else:
                self.success_notification(self._press_release_record, translated_entities, errors)
                logger.info(f"Skipping nats and notification for test run due to TEST_RUN having value {Config.TEST_RUN}")
        except Exception as error:
            if(Config.RECON_MODE == "true" ):
                logger.error(f"Error in recon flow {error}")
                self.error_notification("EU", error=f"Error in recon flow {error}")
                logger.info("Recon Error email sent")
            else:
                email_error = f"""Error while extraction for URL: {self._press_release_record.get("pressReleaseUrl")} with exception {error}"""
                logger.error(email_error)
                self._press_release_record = eu_common_utils.update_pr(self._press_release_record)
                self._press_release_record, error = eu_common_utils.update_exception(self._press_release_record, email_error)
                pr_collection.update_one({"pressReleaseUrl": self._press_release_record.get("pressReleaseUrl"), "listId": self._press_release_record.get("listId")}, {"$set": self._press_release_record})
                self.error_notification("EU", error=error)
                logger.info("Error email sent and PR entry updated with error")