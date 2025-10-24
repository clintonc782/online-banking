from django.contrib import admin
from .models import User, BankAccount, VerificationToken, Message, CardRequest, Transaction, PaymentDetails
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.shortcuts import redirect
from django import forms





@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'email_verified', 'date_of_birth', 'phone_number')
    list_filter = ('is_active', 'email_verified', 'gender', 'date_of_birth', 'country')
    search_fields = ('username', 'email', 'phone_number', 'social_security_number')
    actions = ['freeze_bank_accounts', 'unfreeze_bank_accounts']

    def freeze_bank_accounts(self, request, queryset):
        count = 0
        for user in queryset:
            try:
                account = BankAccount.objects.get(user=user)
                account.is_frozen = True
                account.save()
                count += 1
            except BankAccount.DoesNotExist:
                pass
        self.message_user(request, f"{count} bank accounts have been frozen.")
    freeze_bank_accounts.short_description = "Freeze selected users' bank accounts"

    def unfreeze_bank_accounts(self, request, queryset):
        count = 0
        for user in queryset:
            try:
                account = BankAccount.objects.get(user=user)
                account.is_frozen = False
                account.save()
                count += 1
            except BankAccount.DoesNotExist:
                pass
        self.message_user(request, f"{count} bank accounts have been unfrozen.")
    unfreeze_bank_accounts.short_description = "Unfreeze selected users' bank accounts"


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


class MessageAdmin(admin.ModelAdmin):
    list_display = ("user", "sender", "short_content", "created_at")
    list_filter = ("sender", "created_at")
    search_fields = ("user__username", "content")
    readonly_fields = ("user", "sender", "created_at", "conversation", "reply_section")

    def short_content(self, obj):
        return obj.content[:50]
    short_content.short_description = "Message Preview"

    def conversation(self, obj):
        """Render WhatsApp-like conversation."""
        msgs = Message.objects.filter(user=obj.user).order_by("created_at")
        chat_html = """
        <style>
            .chat-box {
                max-height: 450px;
                overflow-y: auto;
                border: 1px solid #ccc;
                padding: 10px;
                border-radius: 8px;
                background: #f9f9f9;
                scroll-behavior: smooth;
            }
            .msg {
                clear: both;
                padding: 8px 12px;
                margin: 6px 0;
                border-radius: 15px;
                display: inline-block;
                max-width: 70%;
                word-wrap: break-word;
            }
            .admin-msg {
                background: #dcf8c6;
                float: right;
                text-align: right;
            }
            .user-msg {
                background: #e4e6eb;
                float: left;
                text-align: left;
            }
            .msg-time {
                font-size: 11px;
                color: #777;
                display: block;
                margin-top: 4px;
            }
        </style>
        <div class="chat-box" id="chatBox">
        """

        for msg in msgs:
            chat_html += f"""
                <div class="msg {'admin-msg' if msg.sender == 'Admin' else 'user-msg'}">
                    <strong>{'Admin' if msg.sender == 'Admin' else msg.user.username}:</strong>
                    <br>{msg.content}
                    <span class="msg-time">{msg.created_at.strftime('%b %d, %Y %H:%M')}</span>
                </div>
            """

        chat_html += "</div>"
        chat_html += """
        <script>
            document.addEventListener("DOMContentLoaded", function() {
                var chatBox = document.getElementById("chatBox");
                chatBox.scrollTop = chatBox.scrollHeight;
            });
        </script>
        """
        return mark_safe(chat_html)
    conversation.short_description = "Conversation"

    def reply_section(self, obj):
        """Admin reply box."""
        return mark_safe(f"""
            <form method="post" style="margin-top:20px;">
                <input type="hidden" name="_reply_action" value="1">
                <textarea name="reply_content" rows="3" cols="60"
                    placeholder="Type your reply..." required
                    style="border-radius:8px; padding:8px; width:70%;"></textarea><br>
                <button type="submit" class="default" style="margin-top:8px;">Send Reply</button>
            </form>
        """)
    reply_section.short_description = "Reply to user"

    def response_change(self, request, obj):
        """Handle reply submissions from admin."""
        if "_reply_action" in request.POST:
            reply_text = request.POST.get("reply_content")
            if reply_text:
                Message.objects.create(
                    user=obj.user,
                    sender="Admin",
                    content=reply_text,
                    parent=obj.parent or obj
                )
                self.message_user(request, "Reply sent successfully!")
            return redirect(request.path)
        return super().response_change(request, obj)

    def get_fields(self, request, obj=None):
        if obj:
            return ("user", "sender", "conversation", "reply_section")
        return ("user", "sender", "content")


admin.site.register(Message,MessageAdmin)


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


@admin.register(PaymentDetails)
class PaymentDetailsAdmin(admin.ModelAdmin):
    list_display = ("paypal_email", "cashapp_tag", "bitcoin_address", "active", "updated_at")
    list_editable = ("active",)
    ordering = ("-updated_at",)