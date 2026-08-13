from django import forms
from django.utils.translation import gettext_lazy as _

from users.legal import build_legal_consent_record, legal_links_required


class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    accept_terms = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        if legal_links_required() and not cleaned_data.get('accept_terms'):
            self.add_error(
                'accept_terms',
                _('You must accept the terms to create an account.'),
            )
        return cleaned_data

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if legal_links_required():
            user.legal_consent = build_legal_consent_record()
        user.save()
        return user

class UseAdminInviteForm(forms.Form):
    """
    Dummy form that just tells admins to use the Django admin to send invites.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove any fields; we only want to show a message
        self.fields.clear()

    def as_widget(self):
        # This is not needed; we’ll just use a template
        pass
