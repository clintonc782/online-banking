from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.core.paginator import Paginator
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from .forms import UserRegistrationForm, MessageForm, TransferForm, TransactionPinForm
from .models import BankAccount, Message, VerificationToken, Transaction, CardRequest, User, PaymentDetails
from .utils import process_transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Sum






# Logger setup
logger = logging.getLogger(__name__)



def index(request):
    logger.debug(f"Index page accessed by user: {request.user}")
    logger.info(f"{request.user.username} did X from IP: {request.META.get('REMOTE_ADDR')}")
    return render(request, 'accounts/index.html')


def register(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            if User.objects.filter(email=form.cleaned_data['email']).exists():
                messages.error(request, "Email already exists.")
                return redirect('register')
            if User.objects.filter(username=form.cleaned_data['username']).exists():
                messages.error(request, "Username already exists.")
                return redirect('register')

            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = True
            user.save()

            try:
                BankAccount.objects.create(user=user, account_type='savings', balance=0.00)
            except Exception as e:
                logger.error(f"Error creating bank account for user {user.username}: {e}")
                user.delete()
                messages.error(request, "Error creating bank account. Please try again.")
                return redirect('register')

            # try:
            #     send_verification_email(request, user)
            #     messages.success(request, "Registration successful! Please check your email to verify your account.")
            # except Exception as e:
            #     logger.error(f"Error sending verification email: {e}")
            #     user.delete()
            #     messages.error(request, "Error sending verification email. Please try again.")
            #     return redirect('register')

            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def send_verification_email(request, user):
    try:
        token, _ = VerificationToken.objects.get_or_create(user=user)
        verification_link = request.build_absolute_uri(reverse('verify_email', args=[token.token]))
        subject = 'Verify Your Email'
        html_message = render_to_string('accounts/email_verification.html', {
            'user': user,
            'verification_link': verification_link,
        })
        email = EmailMessage(
            subject,
            html_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.content_subtype = 'html'
        email.send(fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send email to {user.email}: {e}", exc_info=True)
        raise e  # re-raise to be caught in register view



def verify_email(request, token):
    try:
        verification_token = VerificationToken.objects.get(token=token)
        user = verification_token.user
        user.email_verified = True
        user.is_active = True
        user.save()
        verification_token.delete()
        messages.success(request, "Your email has been verified successfully! You can now log in.")
        return redirect('login')
    except VerificationToken.DoesNotExist:
        messages.error(request, "Invalid or expired verification link.")
        return redirect('index')


def login_view(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user:
                return render(request, 'accounts/login.html', {
                    'form': form,
                    'error': 'Please verify your email before logging in.'
                })

            login(request, user)

            # Check if bank account exists
            try:
                bank_account = BankAccount.objects.get(user=user)
            except BankAccount.DoesNotExist:
                messages.error(request, "Bank account not found. Please contact support.")
                return redirect('index')

            # Notify user if account is frozen, but allow login
            if bank_account == 'Frozen':
                messages.warning(request, "Your account is currently frozen. Some features may be restricted.")

            return redirect('dashboard')

    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})



def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('index')


@login_required
def dashboard(request):
    try:
        account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        messages.error(request, "Bank account not found. Please contact support.")
        return redirect('index')

    # Fetch latest messages, transactions, card requests
    messages_list = Message.objects.filter(user=request.user).order_by('-created_at')[:10]
    transactions = Transaction.objects.filter(account=account).order_by('-date')[:10]
    card_requests = CardRequest.objects.filter(user=request.user).order_by('-date_requested')
    unread_messages = Message.objects.filter(user=request.user, sender='Admin', is_read=False).count()

    if request.method == 'POST':
        if 'withdraw' in request.POST:
            with transaction.atomic():
                account.is_frozen = True
                account.save()
            logger.info(f"Account {account.account_number} frozen by {request.user.username}.")
            messages.success(request, "Your account has been frozen for withdrawal.")
            return redirect('dashboard')

        elif 'request_card' in request.POST:
            CardRequest.objects.create(user=request.user, status='pending')
            logger.info(f"Card request submitted by {request.user.username}.")
            messages.success(request, "Your card request has been submitted.")
            return redirect('dashboard')

        elif 'reply_to' in request.POST:
            reply_to_id = request.POST.get('reply_to')
            reply_content = request.POST.get('reply_content')

            if reply_to_id and reply_content:
                try:
                    parent_message = Message.objects.get(id=reply_to_id, user=request.user)
                    Message.objects.create(
                        user=request.user,
                        sender=request.user.username,  # Use actual username
                        content=reply_content,
                        is_reply=True,
                        parent=parent_message  # Link reply to original message
                    )
                    logger.info(f"User {request.user.username} replied to message ID {reply_to_id}.")
                    messages.success(request, "Reply sent.")
                except Message.DoesNotExist:
                    messages.error(request, "Original message not found.")
            else:
                messages.error(request, "Reply failed. Content missing.")
            return redirect('dashboard')

    return render(request, 'accounts/dashboard.html', {
        'account': account,
        'messages': messages_list,
        'transactions': transactions,
        'card_requests': card_requests,
        'unread_messages': unread_messages,
    })


@login_required
@transaction.atomic
def transfer_money(request):
    sender_account = get_object_or_404(BankAccount, user=request.user)

    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            receiver_account_number = form.cleaned_data['recipient_account_number']
            amount = Decimal(form.cleaned_data['amount'])
            description = form.cleaned_data.get('description', 'Fund Transfer')

            # ✅ 1. Check if sender’s account is frozen
            if sender_account.status == "Frozen":
                messages.error(request, "Your account is currently frozen. Transfers are disabled.")
                return redirect('dashboard')

            # ✅ 2. Transaction PIN verification
            entered_pin = request.POST.get("pin")

            if not entered_pin:
                messages.error(request, "Please enter your transaction PIN.")
                return redirect("transfer_money")

            # Check the entered PIN against the hashed one in the database
            if not check_password(entered_pin, sender_account.transaction_pin):
                messages.error(request, "Incorrect transaction PIN. Please try again.")
                return redirect("transfer_money")

            # ✅ 3. Validate recipient
            try:
                receiver_account = BankAccount.objects.select_for_update().get(account_number=receiver_account_number)
            except BankAccount.DoesNotExist:
                messages.error(request, "Recipient account not found.")
                return redirect('transfer_money')

            # Prevent self-transfer
            if sender_account == receiver_account:
                messages.error(request, "You cannot transfer to your own account.")
                return redirect('transfer_money')

            # Check both accounts' status
            if sender_account.status != 'Active':
                messages.error(request, "Your account is not active.")
                return redirect('transfer_money')

            if receiver_account.status != 'Active':
                messages.error(request, "Recipient’s account is not active.")
                return redirect('transfer_money')

            # Check sufficient funds
            if sender_account.balance < amount:
                messages.error(request, "Insufficient funds.")
                return redirect('transfer_money')

            # ✅ 4. Perform transfer safely
            with transaction.atomic():
                sender_account.balance -= amount
                receiver_account.balance += amount
                sender_account.save()
                receiver_account.save()

                # ✅ 5. Record transactions for both accounts
                Transaction.objects.create(
                    account=sender_account,
                    amount=amount,
                    type='debit',
                    description=f'Transfer to {receiver_account.account_number} - {description}'
                )
                Transaction.objects.create(
                    account=receiver_account,
                    amount=amount,
                    type='credit',
                    description=f'Transfer from {sender_account.account_number} - {description}'
                )

            # ✅ 6. Notify sender via email
            send_mail(
                subject="Transfer Notification",
                message=(
                    f"Dear {request.user.first_name},\n\n"
                    f"You have successfully transferred ₦{amount:.2f} "
                    f"to account {receiver_account_number}.\n\n"
                    "Thank you for using our services.\n\nBest regards,\nStarlink Bank"
                ),
                from_email="skybank604@gmail.com",
                recipient_list=[request.user.email],
                fail_silently=True,
            )

            messages.success(request, f"₦{amount:.2f} successfully transferred to {receiver_account.user.first_name}.")
            logger.info(f"User {request.user.username} transferred ₦{amount:.2f} to {receiver_account_number}.")
            return redirect('dashboard')
    else:
        form = TransferForm()

    # ✅ Include account for template display
    return render(request, 'accounts/transfer.html', {
        'form': form,
        'account': sender_account,})



@login_required
def verify_account(request, account_number):
    try:
        account = BankAccount.objects.get(account_number=account_number)
        full_name = f"{account.user.first_name} {account.user.last_name}"
        return JsonResponse({"success": True, "name": full_name})
    except BankAccount.DoesNotExist:
        return JsonResponse({"success":False})



@login_required
@transaction.atomic
def set_transaction_pin(request):
    account = get_object_or_404(BankAccount, user=request.user)

    if request.method == "POST":
        pin = request.POST.get("pin")
        confirm_pin = request.POST.get("confirm_pin")

        if not pin or not confirm_pin:
            messages.error(request, "Both PIN fields are required.")
            return redirect("set_transaction_pin")

        if pin != confirm_pin:
            messages.error(request, "PINs do not match. Please try again.")
            return redirect("set_transaction_pin")

        if len(pin) != 6 or not pin.isdigit():
            messages.error(request, "PIN must be exactly 6 digits.")
            return redirect("set_transaction_pin")

        try:
            # Hash the PIN before saving (for security)
            hashed_pin = make_password(pin)

            if account.transaction_pin:
                account.transaction_pin = hashed_pin
                account.save(update_fields=["transaction_pin"])
                messages.success(request, "Your transaction PIN has been updated successfully.")
            else:
                account.transaction_pin = hashed_pin
                account.save(update_fields=["transaction_pin"])
                messages.success(request, "Your transaction PIN has been created successfully.")

            return redirect("dashboard")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return render(request, "accounts/set_transaction_pin.html", {"account":account})



@login_required
def user_messages(request):
    """
    User chat page — displays message thread and allows sending new messages.
    Admin replies appear in real-time (via fetch_messages).
    """
    messages_list = Message.objects.filter(user=request.user).order_by('created_at')

    # Mark all unread admin messages as read
    unread_admin_messages = messages_list.filter(sender='Admin', is_read=False)
    unread_admin_messages.update(is_read=True)

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.user = request.user
            msg.sender = "User"
            msg.parent = Message.objects.filter(user=request.user, parent__isnull=True).last()
            msg.save()
            messages.success(request, "Message sent successfully.")
            return redirect('user_messages')
    else:
        form = MessageForm()

        # If request comes from AJAX refresh (for live update)
    if request.GET.get('ajax'):
        return render(request, 'accounts/partials/_chat_messages.html', {
            'messages_list': messages_list,
        })

    return render(request, 'accounts/messages.html', {
        'messages_list': messages_list,
        'form': form
    })


@login_required
def fetch_messages(request):
    """
    AJAX endpoint that returns new messages since the last known timestamp.
    The frontend will hit this periodically (every few seconds).
    """
    last_msg_time = request.GET.get('last_time')
    user = request.user

    if last_msg_time:
        new_msgs = Message.objects.filter(
            user=user,
            created_at__gt=last_msg_time
        ).order_by('created_at')
    else:
        new_msgs = Message.objects.filter(user=user).order_by('created_at')

    data = [
        {
            'sender': msg.sender,
            'content': msg.content,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for msg in new_msgs
    ]

    return JsonResponse({'new_messages': data})


@login_required
def unread_messages_count(request):
    """
    Used to show notification badge (e.g. in navbar).
    Returns count of unread admin messages.
    """
    count = Message.objects.filter(
        user=request.user,
        sender='Admin',
        is_read=False
    ).count()
    return JsonResponse({'unread_count':count})

@login_required
@transaction.atomic
def top_up(request):
    account = get_object_or_404(BankAccount, user=request.user)
    payment = PaymentDetails.objects.filter(active=True).order_by("-updated_at").first()

    # Prevent top-up if account is frozen or inactive
    if account.status.lower() in ['frozen', 'inactive']:
        messages.error(request, "Your account is currently frozen or inactive. You cannot top up at the moment.")
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount'))

            if amount <= 0:
                messages.error(request, "Please enter a valid amount greater than zero.")
                return redirect('top_up')

            # Safely credit the account
            process_transaction(account, amount, 'credit', 'Top-up from external source')

            # Optional: send confirmation email (like in transfer)
            send_mail(
                subject="Top-Up Successful",
                message=(
                    f"Dear {request.user.first_name},\n\n"
                    f"₦{amount:.2f} has been successfully added to your account.\n\n"
                    "Thank you for banking with us.\n\nBest regards,\nSkyBank"
                ),
                from_email="skybank604@gmail.com",
                recipient_list=[request.user.email],
                fail_silently=True,
            )

            messages.success(request, f"₦{amount:.2f} has been added to your account.")
            return redirect('dashboard')

        except (ValueError, TypeError):
            messages.error(request, "Invalid top-up amount.")
        except ValidationError as e:
            messages.error(request, str(e))

    return render(request, 'accounts/top_up.html', {'account': account, "payment": payment})



@login_required
@transaction.atomic
def deposit(request):
    account = get_object_or_404(BankAccount, user=request.user)
    payment = PaymentDetails.objects.filter(active=True).order_by("-updated_at").first()

    # Prevent deposit if account is frozen or inactive
    if account.status.lower() in ['frozen', 'inactive']:
        messages.error(request, "Your account is currently frozen or inactive. You cannot deposit funds.")
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount'))

            if amount <= 0:
                messages.error(request, "Please enter a valid deposit amount greater than zero.")
                return redirect('deposit')

            # Record transaction
            process_transaction(account, amount, 'credit', 'Cash deposit')

            # Optional: confirmation email
            send_mail(
                subject="Deposit Successful",
                message=(
                    f"Dear {request.user.first_name},\n\n"
                    f"Your deposit of ₦{amount:.2f} has been successfully credited to your account.\n\n"
                    "Thank you for banking with us.\n\nBest regards,\nSkyBank"
                ),
                from_email="skybank604@gmail.com",
                recipient_list=[request.user.email],
                fail_silently=True,
            )

            messages.success(request, f"₦{amount:.2f} deposited successfully.")
            return redirect('dashboard')

        except (ValueError, TypeError):
            messages.error(request, "Invalid deposit amount.")
        except ValidationError as e:
            messages.error(request, str(e))

    return render(request, 'accounts/deposit.html', {'account':account, 'payment':payment})



@login_required
def transaction_history(request):
    account = get_object_or_404(BankAccount, user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-date')
    total_credit = transactions.filter(type='credit').aggregate(Sum('amount'))['amount__sum'] or 0
    total_debit = transactions.filter(type='debit').aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'accounts/transaction_history.html', {
        'transactions': transactions,
        'account': account,
        'total_credit': total_credit,
        'total_debit': total_debit,
})



def get_recipient_name(request):
    account_number = request.GET.get('account_number', '').strip()
    if account_number:
        try:
            account = BankAccount.objects.get(account_number=account_number, status='Active')
            return JsonResponse({'name': account.user.first_name})
        except BankAccount.DoesNotExist:
            return JsonResponse({'name': ''})
    return JsonResponse({'name': ''})


def privacy_policy(request):
    return render(request, 'accounts/privacy_policy.html')
