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





class TransferForm(forms.Form):
    recipient_account_number = forms.CharField(max_length=12, label="Recipient Account Number")
    amount = forms.DecimalField(max_digits=10, decimal_places=2, label="Amount")
    description = forms.CharField(max_length=225, required=False)

# Message Form
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'content']
        widgets = {
            'subject': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Subject'}),
            'content': forms.Textarea(attrs={'class':'form-control', 'placeholder': 'Type your message here...', 'rows': 3, }),
        }


class TransactionPinForm(forms.Form):
    current_pin = forms.CharField(
        max_length=6,
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Current PIN (leave blank if none)'}),
        label="Current PIN"
    )
    new_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new 4-6 digit PIN'}),
        label="New PIN"
    )
    confirm_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new PIN'}),
        label="Confirm New PIN"
    )

    def clean(self):
        cleaned_data = super().clean()
        new_pin = cleaned_data.get('new_pin')
        confirm_pin = cleaned_data.get('confirm_pin')

        if new_pin != confirm_pin:
            raise forms.ValidationError("New PIN and confirmation PIN do not match.")

        if not new_pin.isdigit() or not (4 <= len(new_pin) <= 6):
            raise forms.ValidationError("PIN must be 4 to 6 digits only.")

        return cleaned_data