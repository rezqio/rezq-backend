import logging
from multiprocessing import Process

from django.core.mail import EmailMultiAlternatives
from server.constants import EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES
from server.constants import FROM_EMAIL_ADDRESS
from server.constants import PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)


class EmailProcess(Process):
    def __init__(
        self,
        subject,
        text_content,
        html_content,
        from_address,
        to_address,
    ):
        self.subject = subject
        self.text_content = text_content
        self.html_content = html_content
        self.from_address = from_address
        self.to_address = to_address

        Process.__init__(self)

    def run(self):
        try:
            email = EmailMultiAlternatives(
                self.subject,
                self.text_content,
                self.from_address,
                [self.to_address],
            )
            email.attach_alternative(self.html_content, 'text/html')
            email.send()
        except Exception as e:
            logger.error(f'{type(e)}: {str(e)}')


def send_password_reset_mail(email, reset_link):
    subject = 'Reset your RezQ password'
    text_content = (
        f'Visit {reset_link} to reset your password. '
        'This link will expire in '
        f'{PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.'
    )
    html_content = get_email_template_html(
        'Reset your RezQ password',
        (
            'Click on the link below to reset your password. '
            'The link will expire in '
            f'{PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.'
        ),
        reset_link,
        'Reset Password',
    )

    EmailProcess(
        subject,
        text_content,
        html_content,
        FROM_EMAIL_ADDRESS,
        email,
    ).start()


def send_email_verification_mail(email, verfication_link):
    subject = 'Verify your RezQ email'
    text_content = (
        f'Visit {verfication_link} to verify your email. '
        f'This link will expire in '
        f'{EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.'
    )
    html_content = get_email_template_html(
        'Verify your RezQ email',
        (
            'Click on the link below to verify your email. '
            'The link will expire in '
            f'{EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.'
        ),
        verfication_link,
        'Verify Email',
    )

    EmailProcess(
        subject,
        text_content,
        html_content,
        FROM_EMAIL_ADDRESS,
        email,
    ).start()


def send_critique_completed_notif_mail(email, resume_name, unsubscribe_link):
    subject = 'Your critique is ready!'
    text_content = (
        f'Good news, your resume {resume_name} has a new critique. '
        'Go to RezQ to check it out!'
        '\n\n'
        'To unsubscribe from email notifcations, '
        f'visit {unsubscribe_link}.'
    )
    html_content = get_email_template_html(
        'Your critique is ready!',
        'Good news, your resume has a new critique.',
        'https://rezq.io/resumes',
        'View Now',
        unsubscribe_link,
    )

    EmailProcess(
        subject,
        text_content,
        html_content,
        FROM_EMAIL_ADDRESS,
        email,
    ).start()


def send_critiquer_matched_notif_mail(email, unsubscribe_link):
    subject = 'You\'ve been matched!'
    text_content = (
        'Good news, you have a new resume to critique. '
        'You can now go to RezQ to critique this resume.'
        '\n\n'
        'To unsubscribe from email notifcations, '
        f'visit {unsubscribe_link}.'
    )
    html_content = get_email_template_html(
        'You\'ve been matched!',
        'Good news, you have a new resume to critique.',
        'https://rezq.io/critiques',
        'View Now',
        unsubscribe_link,
    )

    EmailProcess(
        subject,
        text_content,
        html_content,
        FROM_EMAIL_ADDRESS,
        email,
    ).start()


def get_email_template_html(
    title,
    message,
    button_link,
    button_text,
    unsubscribe_link=None,
):
    return (
        '<html>'
        '<body>'
        '<font face="Helvetica Neue" color="000000">'
        '<div style="background-color: #fafafa; padding: 10px;'
        'height: 100%; width: 100%;">'
        '<table width="100%" border="0" cellspacing="0" cellpadding="0">'
        '<tr>'
        '<td align="center">'
        '<table height="450px" width="500px" border="0" cellspacing="0"'
        'cellpadding="0" bgcolor="ffffff">'
        '<tr>'
        '<td align="center">'
        '<div style="padding: 0px 100px;">'
        '<img src="https://rezq.io/logo.png" style="width: 240px;"></img>'
        f'<p style="font-size: 30px;">{title}</p>'
        '<table bgcolor="#ffb91b" height="5px" width="300px">'
        '<tr><td></td></tr></table>'
        '<p style="font-size: 14px; padding-bottom: 20px;">'
        f'{message}'
        '</p>'
        f'<a href="{button_link}" style="text-decoration: none; color: #fff;">'
        '<div style="background-color: #d21280; width: 200px; font-size: 18px;'
        'font-weight: 400; cursor: pointer; padding: 25px 0px;">'
        f'{button_text}'
        '</div>'
        '</a>'
    ) + (
        (
            '<div style="text-align: center; font-size: 10px;'
            'margin-top: 50px;">'
            f'<a href="{unsubscribe_link}">'
            'Unsubscribe from email notifications</a>'
            '</div>'
        ) if unsubscribe_link else ''
    ) + (
        '</td>'
        '</tr>'
        '</table>'
        '</div>'
        '</font>'
        '</body>'
        '</html>'
    )
