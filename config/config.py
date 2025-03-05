import os
from dotenv import load_dotenv
 
# Load environment variables from .env file
load_dotenv()
 
# Optionally, define a Config class to store configurations
class Config:
    ENV = os.getenv('ENV')
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
    MONGO_URL=os.getenv("MONGO_URL")
    MONGO_DB=os.getenv("MONGO_DB", "pressMonitorDB")
    PR_COLLECTION=os.getenv("PR_COLLECTION", "pressReleaseReference")
    ENTITY_COLLECTION=os.getenv("ENTITY_COLLECTION", "pressReleaseList")
    MONITOR_CONFIG_COLLECTION=os.getenv("MONITOR_CONFIG_COLLECTION")
    MONITOR_DETAILS_COLLECTION=os.getenv("MONITOR_DETAILS_COLLECTION", "prMonitorDetails")
    EU_RSS_URL=os.getenv("EU_RSS_URL")
    NATS_SERVER=os.getenv("NATS_SERVER")
    NATS_USERNAME=os.getenv("NATS_USERNAME")
    NATS_PASSWORD=os.getenv("NATS_PASSWORD")
    NATS_EU_SUBJECT=os.getenv("NATS_EU_SUBJECT", "LISTUPDATES.LIST.EU_PR.UPDATE")
    
    AWS_REGION=os.getenv("AWS_REGION")
    SENDER_EMAIL=os.getenv("SENDER_EMAIL", "noreply@facctum.com")
    TO_EMAILS=os.getenv("TO_EMAILS", "vikas.saini@facctum.com")
    TO_EMAILS_ERROR=os.getenv("TO_EMAILS_ERROR", "vikas.saini@facctum.com")
    EXTRA_TITLE=os.getenv("EXTRA_TITLE", "")
    
    
    USE_TEST_DB = os.getenv("USE_TEST_DB", "false")
    TEST_RUN = os.getenv("TEST_RUN", "false")
    MOCK_S3 = os.getenv("MOCK_S3", False)
    MOCK_NATS = os.getenv("MOCK_NATS", False)
    
    
    LIST_ID = os.getenv("LIST_ID", False)
    GUID = os.getenv("GUID", False)
    S3_BUCKET = os.getenv("S3_BUCKET", False)
    RUN_ID = os.getenv("RUN_ID", False)
    RECON_MODE = os.getenv("RECON_MODE", False)
    RECON_FILE_PATH = os.getenv("RECON_FILE_PATH")