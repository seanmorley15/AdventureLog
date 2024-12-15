from django import forms

class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    def signup(self, request, user):
        # Delay the import to avoid circular import
        from allauth.account.forms import SignupForm

        # No need to call super() from CustomSignupForm; use the SignupForm directly if needed
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Save the user instance
        user.save()
        return user