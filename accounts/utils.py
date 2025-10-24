from django.db import transaction
from django.core.exceptions import ValidationError
from .models import BankAccount, Transaction

def process_transaction(account, amount, transaction_type, description):
    """
    Safely process a credit or debit transaction for an account.
    - account: BankAccount instance
    - amount: positive float value
    - transaction_type: 'credit' or 'debit'
    - description: string explaining the transaction
    """
    if amount <= 0:
        raise ValidationError("Amount must be positive.")

    if transaction_type not in ['credit', 'debit']:
        raise ValidationError("Invalid transaction type.")

    with transaction.atomic():
        account = BankAccount.objects.select_for_update().get(pk=account.pk)

        if transaction_type == 'debit' and account.balance < amount:
            raise ValidationError("Insufficient funds.")

        if transaction_type == 'credit':
            account.balance += amount
        else:
            account.balance -= amount

        account.save()

        Transaction.objects.create(
            account=account,
            amount=amount,
            type=transaction_type,
            description=description
        )

    return account