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



from .forms import UserRegistrationForm, MessageForm
from .models import BankAccount, Message, VerificationToken, Transaction, CardRequest, User

# Logger setup
logger = logging.getLogger(__name__)


def index(request):
    logger.debug(f"Index page accessed by user: {request.user}")
    return render(request, 'accounts/index.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

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
            user.is_active = False
            user.save()

            try:
                BankAccount.objects.create(user=user)
            except Exception as e:
                logger.error(f"Error creating bank account for user {user.username}: {e}")
                user.delete()
                messages.error(request, "Error creating bank account. Please try again.")
                return redirect('register')

            try:
                send_verification_email(user)
                messages.success(request, "Registration successful! Please check your email to verify your account.")
            except Exception as e:
                logger.error(f"Error sending verification email: {e}")
                user.delete()
                messages.error(request, "Error sending verification email. Please try again.")
                return redirect('register')

            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def send_verification_email(user):
    token, _ = VerificationToken.objects.get_or_create(user=user)
    verification_link = f"http://127.0.0.1:8000/accounts/verify/{token.token}/"
    subject = 'Verify Your Email'
    html_message = render_to_string('accounts/email_verification.html', {
        'user': user,
        'verification_link': verification_link,
    })
    email = EmailMessage(
        subject,
        html_message,
        'skybank604@gmail.com',
        [user.email],
    )
    email.content_subtype = 'html'  # This sends the email as HTML
    email.send(fail_silently=False)


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
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email_verified:
                return render(request, 'accounts/login.html', {'form': form, 'error': 'Please verify your email before logging in.'})
            login(request, user)
            if not BankAccount.objects.filter(user=user).exists():
                messages.error(request, "Bank account not found. Please contact support.")
                return redirect('index')
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

    messages_list = Message.objects.filter(user=request.user).order_by('-created_at')[:5]
    transactions = Transaction.objects.filter(account=account).order_by('-date')[:10]

    if request.method == 'POST':
        if 'withdraw' in request.POST:
            account.is_frozen = True
            account.save()
            logger.info(f"Account {account.account_number} has been frozen for withdrawal by {request.user.username}.")
            messages.success(request, "Your account has been frozen for withdrawal.")
            return redirect('dashboard')
        if 'request_card' in request.POST:
            CardRequest.objects.create(user=request.user, status='Pending')
            logger.info(f"Card request submitted by {request.user.username}.")
            messages.success(request, "Your card request has been submitted.")
            return redirect('dashboard')

    return render(request, 'accounts/dashboard.html', {
        'account': account,
        'messages': messages_list,
        'transactions': transactions,
    })


@login_required
def transfer_money(request):
    if request.method == 'POST':
        receiver_account_number = request.POST.get('receiver_account')
        try:
            amount = float(request.POST.get('amount'))
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            return render(request, 'accounts/transfer.html', {'error': 'Invalid amount.'})

        sender_account = BankAccount.objects.get(user=request.user)
        receiver_account = get_object_or_404(BankAccount, account_number=receiver_account_number)

        if sender_account == receiver_account:
            return render(request, 'accounts/transfer.html', {'error': 'Cannot transfer to the same account.'})

        if sender_account.balance < amount:
            return render(request, 'accounts/transfer.html', {'error': 'Insufficient balance.'})

        with transaction.atomic():
            sender_account.balance -= amount
            receiver_account.balance += amount
            sender_account.save()
            receiver_account.save()

        send_mail(
            subject="Transfer Notification",
            message=(
                f"Dear {request.user.first_name},\n\n"
                f"You have successfully transferred ${amount:.2f} to account {receiver_account_number}.\n\n"
                "Thank you for using our services.\n\nBest regards,\nYour Bank"
            ),
            from_email="noreply@onlinebanking.com",
            recipient_list=[request.user.email],
            fail_silently=False,
        )

        logger.info(f"User {request.user.username} transferred ${amount:.2f} to account {receiver_account_number}.")
        messages.success(request, "Transfer successful!")
        return redirect('dashboard')

    return render(request, 'accounts/transfer.html')


@login_required
def user_messages(request):
    messages_list = Message.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(messages_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/messages.html', {'page_obj': page_obj})


@login_required
def send_message(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.user = request.user
            message.sender = 'User'
            message.save()
            logger.info(f"Message sent by {request.user.username}.")
            messages.success(request, "Your message has been sent to the admin.")
            return redirect('user_messages')
    else:
        form = MessageForm()
    return render(request, 'accounts/send_message.html', {'form': form})


@login_required
def top_up(request):
    if request.method == 'POST':
        # Top-up logic here
        messages.success(request, "Your account has been topped up successfully.")
        return redirect('dashboard')
    return render(request, 'accounts/top_up.html')


@login_required
def deposit(request):
    if request.method == 'POST':
        # Deposit logic here
        messages.success(request, "Deposit successful.")
        return redirect('dashboard')
    return render(request, 'accounts/deposit.html')


@login_required
def transaction_history(request):
    account = BankAccount.objects.get(user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-date')
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/transaction_history.html', {'page_obj': page_obj})


def privacy_policy(request):
    return render(request, 'accounts/privacy_policy.html')
