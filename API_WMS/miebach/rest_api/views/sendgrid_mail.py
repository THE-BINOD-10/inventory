import os
import base64
import zipfile
import smtplib
from sendgrid import SendGridAPIClient
from miebach_utils import init_logger
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders, Encoders
from sendgrid.helpers.mail import *




log = init_logger('logs/sendgrid_mail.log')


def send_sendgrid_mail(from_address, send_to, subject, text, files=[]):
    try:
        if isinstance(send_to,list):
            send_to = [i for i in send_to if i]
        send_to= list(set(send_to))
        to_list = Personalization()
        to_list.add_to(Email(send_to[0]))
        if len(send_to) > 1:
            for email in send_to[1:]:
                to_list.add_cc(Email(email))
        from_email = Email(from_address)
        to_email = To(send_to)
        subject = subject
        content = Content("text/html", text)
        mail = Mail(from_email, None, subject, content)
        mail.add_personalization(to_list)
        for f in files:
            if isinstance(f, dict):
                file_path = f['path']
                file_name = f['name']
            else:
                file_path = f
                file_name = f
            file_data = open(file_path, "rb")
            encoded = base64.b64encode(file_data.read())
            attachment = Attachment()
            attachment.file_content = FileContent(encoded)
            attachment.file_type = FileType('application/pdf')
            attachment.file_name = FileName(file_name)
            attachment.disposition = Disposition('attachment')
            attachment.content_id = ContentId(file_name)
            mail.attachment = attachment
        sg = SendGridAPIClient('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')
        response = sg.send(mail)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Sending mail through sendgrid api failed for params" + from_address + " " + subject)


