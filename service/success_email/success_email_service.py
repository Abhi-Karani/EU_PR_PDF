from io import BytesIO
import boto3
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from service.database.database_service import pr_collection
from config.config import Config
from utils.success_email_utils.success_email_df_utils import convert_entities_to_df
from service.logger.logger import get_logger
import os
logger = get_logger("success_email_service")


def send_success_notification(pr,entities,errors=[]):
    
    error_mapper_identifier_extractor = errors
    try:
        if not entities:
            return {
                'email_sent': False,
                'partial_email': False,
                'errors_handled':error_mapper_identifier_extractor
            }
        
        df = convert_entities_to_df(entities)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0) 
        html_data = generate_html(pr)
        logger.info("HTML generation is complete")
       
        msg = MIMEMultipart()
        # Replace these variables with your email information
        sender_email = Config.SENDER_EMAIL
        extra_title = Config.EXTRA_TITLE
        logger.info(extra_title)
        subject = f'[ALERT] {extra_title} Press Release Announcement for EU JOURNAL'
           
            
        msg['Subject'] = subject
        msg.attach(MIMEText(html_data, 'html'))

        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(buffer.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment; filename=data.xlsx')
        msg.attach(attachment)


        if(len(pr) == 0):
            return {
                'email_sent': False,
                'partial_email': False,
                'errors_handled':error_mapper_identifier_extractor
            }
        
        # Create an SES client
        ses = boto3.client('ses', region_name=Config.AWS_REGION)

        recipient_email = Config.TO_EMAILS.split(",")
        
        # Send the HTML email
        response = ses.send_raw_email(
            Source=sender_email,
            Destinations=recipient_email,
            RawMessage={'Data': msg.as_string()
            },
        )

        logger.info("Email sent!")
        logger.info("Email sent to: %s", recipient_email)
      
        
        result = pr_collection.update_one(
            { 'pressReleaseUrl': pr.get('pressReleaseUrl')
            },  
            { '$set': 
                {
                    'email_audit': { 
                        'status' : 'Sent',
                        'timestamp' : datetime.utcnow(),
                        'recipient' :  recipient_email
                    }
                } 
            }  
        )
        logger.info("PR updated with email audit details")
        return {
            'email_sent': True,
            'partial_email': False,
            'errors_handled':error_mapper_identifier_extractor
        }
    except Exception as e:
        error = {
            "error_id":None,
            "error":f"Error encountered while sending email with exception {str(e)}",
            "status":"Emailing Error" 
        }
        logger.error(f"Error in sending success email {e}")
       
        error_mapper_identifier_extractor.append(error)
        recipient_email = Config.TO_EMAILS_ERROR.split(",")
        result = pr_collection.update_one(
            { 'pressReleaseUrl': pr.get('pressReleaseUrl')
            },  
            { '$set': 
                {
                    'email_audit': { 
                        'status' : 'Failed',
                        'timestamp' : datetime.utcnow(),
                        'recipient' :  recipient_email
                    }
                } 
            }  
        )
        logger.info(f"PR updated with error details")
        return {
            "email_sent": False,
            "partial_email": True,
            'errors_handled':error_mapper_identifier_extractor
        }


def generate_html(pr):
    logger.info("HTML generation started")
    html_body = "This is an automated notification to inform you that new press release(s) for the EU Journals have been officially announced"
    html_body += "<br/>"
    html_body += "<br/>"
    html_body += f"Please check the attached record details for more information. To view the full announcement(s), visit the following link(s):"
    html_body += "<br/>"
        
    html_body += "<br/>"
    html_body += f"<a style='text-decoration:none; margin:0; padding:0;' href='{pr.get('pressReleaseUrl')}'>{pr.get('pressReleaseTitle')}</a><br/>"

    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    env = Environment(loader=FileSystemLoader(os.path.join(root_dir, 'resources')))

    template = env.get_template("success_email/basic_template_reference.html")
    
    context = {
        "html_body": html_body,
    }

    # Render template with context
    html = template.render(context)
    return html 