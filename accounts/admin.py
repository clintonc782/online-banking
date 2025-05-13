from django.contrib import admin
from .models import User, BankAccount, VerificationToken, Message, CardRequest, Transaction


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'email_verified', 'date_of_birth', 'phone_number')
    list_filter = ('is_active', 'email_verified', 'gender', 'date_of_birth', 'country')
    search_fields = ('username', 'email', 'phone_number', 'social_security_number')
    actions = ['freeze_accounts', 'unfreeze_accounts']

    def freeze_accounts(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected accounts have been frozen.")
    freeze_accounts.short_description = "Freeze selected accounts"

    def unfreeze_accounts(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected accounts have been unfrozen.")
    unfreeze_accounts.short_description = "Unfreeze selected accounts"


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_number', 'account_type', 'balance', 'created_at')
    list_filter = ('account_type', 'created_at')
    search_fields = ('account_number', 'user__username', 'user__email')


@admin.register(VerificationToken)
class VerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'token')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'sender', 'content', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('user__username', 'user__email', 'content')


@admin.register(CardRequest)
class CardRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'date_requested')  # Use 'date_requested' instead of 'created_at'
    search_fields = ('user__username',)
    list_filter = ('status',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'date', 'description', 'amount', 'type')
    search_fields = ('account__account_number', 'description')
    list_filter = ('type', 'date')