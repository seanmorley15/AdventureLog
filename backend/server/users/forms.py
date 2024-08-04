from allauth.account.utils import (filter_users_by_email, user_pk_to_url_str, user_username)
from allauth.utils import build_absolute_uri
from allauth.account.adapter import get_adapter
from allauth.account.forms import default_token_generator
from allauth.account import app_settings
from django.conf import settings

from allauth.account.forms import ResetPasswordForm as AllAuthPasswordResetForm

class CustomAllAuthPasswordResetForm(AllAuthPasswordResetForm):

    def clean_email(self):
        """
        Invalid email should not raise error, as this would leak users
        for unit test: test_password_reset_with_invalid_email
        """
        email = self.cleaned_data["email"]
        email = get_adapter().clean_email(email)
        self.users = filter_users_by_email(email, is_active=True)
        return self.cleaned_data["email"]

    def save(self, request, **kwargs):
        email = self.cleaned_data['email']
        token_generator = kwargs.get('token_generator', default_token_generator)

        for user in self.users:
            temp_key = token_generator.make_token(user)

            path = f"custom_password_reset_url/{user_pk_to_url_str(user)}/{temp_key}/"
            url = build_absolute_uri(request, path)

            frontend_url = settings.FRONTEND_URL
            # remove ' from frontend_url
            frontend_url = frontend_url.replace("'", "")

     #Values which are passed to password_reset_key_message.txt
            context = {
                "frontend_url": frontend_url,
                "user": user,
                "password_reset_url": url,
                "request": request,
                "path": path,
                "temp_key": temp_key,
                'user_pk': user_pk_to_url_str(user),
            }

            if app_settings.AUTHENTICATION_METHOD != app_settings.AuthenticationMethod.EMAIL:
                context['username'] = user_username(user)
            get_adapter(request).send_mail(
                'account/email/password_reset_key', email, context
            )

        return self.cleaned_data['email']
    

