from pymongo import MongoClient
from config.config import Config
from service.logger.logger import get_logger
logger = get_logger("database_service")

def get_database_collections():

    if(Config.USE_TEST_DB == "true"):
        logger.info("Using Test DB because of USE_TEST_DB flag in env")
        client = MongoClient(Config.MONGO_URL)
        database = client[Config.MONGO_DB + "Test"]
        pr_collection = database[Config.PR_COLLECTION + "Test"]
        entity_collection = database[Config.ENTITY_COLLECTION + "Test"]
        monitor_details_collection = database[Config.MONITOR_DETAILS_COLLECTION + "Test"]
        return pr_collection, entity_collection, monitor_details_collection
    else:
        logger.info("Using Actual DB because of USE_TEST_DB flag in env")
        client = MongoClient(Config.MONGO_URL)
        database = client[Config.MONGO_DB]
        pr_collection = database[Config.PR_COLLECTION]
        entity_collection = database[Config.ENTITY_COLLECTION]
        monitor_details_collection = database[Config.MONITOR_DETAILS_COLLECTION]
        return pr_collection, entity_collection, monitor_details_collection

# Initialize collections
pr_collection, entity_collection, monitor_details_collection = get_database_collections()