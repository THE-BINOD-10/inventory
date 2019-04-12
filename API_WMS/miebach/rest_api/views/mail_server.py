import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders, Encoders


def send_mail(send_to, subject, body):
    if not send_to:
        return

    fromaddr = 'noreply@mieone.com'

    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = ', '.join(send_to)
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    part = MIMEBase('application', 'octet-stream')
    encoders.encode_base64(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', '465')
        server.login(fromaddr, "no*reply!59")
        text = msg.as_string()

        server.sendmail(fromaddr, send_to, text)
        server.quit()
    except:
        return


def send_mail_attachment(send_to, subject, text, files=[], compressed=False):
    fromaddr = 'noreply@mieone.com'

    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = ', '.join(send_to)
    msg['Subject'] = subject

    body = text

    NAME_OF_DESTINATION_ARCHIVE = 'compressed'
    msg.attach(MIMEText(body, 'html'))
    if compressed:
        zf = zipfile.ZipFile('%s.zip' %(NAME_OF_DESTINATION_ARCHIVE), 'w', 8)
        for f in files:
            if isinstance(f, dict):
                file_path = f['path']
                file_name = f['name']
            else:
                file_path = f
                file_name = f

            zf.write(file_path, file_name)
        zf.close()
        part = MIMEBase("application", "octet-stream")
        attachment = open(NAME_OF_DESTINATION_ARCHIVE + ".zip", "rb")
        part.set_payload(attachment.read())
        Encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment; filename=\"%s.zip\"" % (NAME_OF_DESTINATION_ARCHIVE))
        msg.attach(part)
    else:
        for f in files:

            if isinstance(f, dict):
                file_path = f['path']
                file_name = f['name']
            else:
                file_path = f
                file_name = f
            attachment = open(file_path, "rb")

            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= %s" % file_name)

            msg.attach(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', '465')
        server.login(fromaddr, "no*reply!59")
        text = msg.as_string()

        server.sendmail(fromaddr, send_to, text)
        server.quit()
    except:
        return
