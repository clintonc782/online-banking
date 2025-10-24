from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from datetime import timedelta
from django.utils.timezone import now


class User(AbstractUser):
    user_id = models.UUIDField(default=uuid.uuid4, editable=False)  # Unique user identifier
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=False)  # Ensure phone numbers are unique
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    date_of_birth = models.DateField(null=True, blank=True)
    street = models.CharField(max_length=255)
    apartment = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)

    # New fields
    next_of_kin = models.CharField(max_length=100, blank=True, null=True)  # Next of Kin
    occupation = models.CharField(max_length=100, blank=True, null=True)  # Occupation

    email_verified = models.BooleanField(default=False)

    # ID Verification Fields
    id_verification_number = models.CharField(max_length=50, blank=True, null=True)  # For ID number
    id_verification_document = models.FileField(upload_to='id_verifications/', blank=True, null=True) # For uploaded ID document
    # transaction_pin = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.email})"


class BankAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=12, unique=True, blank=True)
    account_type = models.CharField(max_length=50, choices=[('Savings', 'Savings'), ('Checking', 'Checking')])
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)  # Track when the account was created
    status = models.CharField(
        max_length=20,
        choices=[('Active', 'Active'), ('Frozen', 'Frozen'), ('Closed', 'Closed')],
        default='Active'
    )
    transaction_pin = models.CharField(max_length=128, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_account_number():
        # Generate a 12-digit account number and ensure uniqueness
        account_number = str(uuid.uuid4().int)[:12]
        while BankAccount.objects.filter(account_number=account_number).exists():
            account_number = str(uuid.uuid4().int)[:12]
        return account_number

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"


class Transaction(models.Model):
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)

    def __str__(self):
        return f"{self.account.account_number} - {self.type} - ${self.amount}"


class CardRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class PaymentDetails(models.Model):
    """
    Site-wide public payment receiving details. There should normally be one active row.
    Owner edits these in admin whenever they want.
    """
    paypal_email = models.EmailField(blank=True, null=True, help_text="PayPal email (public receiving address).")
    cashapp_tag = models.CharField(max_length=100, blank=True, null=True, help_text="CashApp $tag (e.g. $StarlinkPay).")
    bitcoin_address = models.CharField(max_length=200, blank=True, null=True, help_text="Bitcoin (BTC) address.")

    active = models.BooleanField(default=True, help_text="If False, hide from public pages.")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Details"
        verbose_name_plural = "Payment Details"

    def _str_(self):
        return f"Payment details (updated {self.updated_at:%Y-%m-%d%H:%M})"


class VerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # Tokens expire after 24 hours
        return now() > self.created_at + timedelta(hours=24)

    def __str__(self):
        return f"Token for {self.user.username}"


class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=100, choices=[('Admin', 'Admin'), ('User', 'User')], default='User')
    subject = models.CharField(max_length=100, blank=True, null=True)  # Added subject field
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} to {self.user.username} at {self.created_at}"


    class Meta:
        ordering = ['-created_at']

    def lastest_thread(self):
        """ Returns the root message of this user's latest thread. """
        return Message.objects.filter(user=self.user, parent__isnull=True).order_by('-created_at').first()