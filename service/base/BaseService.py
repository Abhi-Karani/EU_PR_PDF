class BaseService:
    
    def extractor(self):
        raise NotImplementedError("Subclasses should implement this!")
    
    def identifier(self):
        raise NotImplementedError("Subclasses should implement this!")

    def transform(self):
        raise NotImplementedError("Subclasses should implement this!")

    def upload_to_s3(self):
        raise NotImplementedError("Subclasses should implement this!")
    
    def success_notification(self):
        raise NotImplementedError("Subclasses should implement this!")
    
    def error_notification(self):
        raise NotImplementedError("Subclasses should implement this!")
   
    def notify_via_nats(self):
        raise NotImplementedError("Subclasses should implement this!")

    def run(self):
        raise NotImplementedError("Subclasses should implement this!")
    
    def audit(self):
        raise NotImplementedError("Subclasses should implement this!")
        
