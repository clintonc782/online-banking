from django import forms
from .models import User, Message




class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'other_names', 'email', 'phone_number',
            'gender', 'date_of_birth', 'next_of_kin', 'occupation',  # Added fields
            'street', 'apartment', 'zip_code', 'country', 'state', 'city',
            'id_verification_number', 'id_verification_document'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(attrs={'placeholder': 'Select Gender'}),
            'next_of_kin': forms.TextInput(attrs={'placeholder': 'Enter Next of Kin'}),
            'occupation': forms.TextInput(attrs={'placeholder': 'Enter Occupation'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        id_verification_number = cleaned_data.get("id_verification_number")
        id_verification_document = cleaned_data.get("id_verification_document")

        if not id_verification_number and not id_verification_document:
            raise forms.ValidationError(
                "You must provide either an ID verification number or upload an ID verification document."
            )

        return cleaned_data

    def clean_id_verification_document(self):
        document = self.cleaned_data.get('id_verification_document')

        if document:
            valid_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            extension = document.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError("Only PDF, JPG, and PNG files are allowed.")
        return document

# Message Form
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'placeholder': 'Type your message here...', 'rows': 4}),
        }