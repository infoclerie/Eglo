from django.contrib import admin

from .models import Activity, Opportunity


class ActivityInline(admin.TabularInline):
    model = Activity
    fields = ("kind", "subject", "due_date", "done", "owner", "notes")
    extra = 1


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "name", "stage", "expected_amount", "probability", "owner", "next_action_date")
    list_filter = ("stage", "owner")
    search_fields = ("title", "prospect_name", "partner__name")
    autocomplete_fields = ["partner"]
    inlines = [ActivityInline]

    def save_model(self, request, obj, form, change):
        stage_changed = change and "stage" in form.changed_data
        super().save_model(request, obj, form, change)
        if stage_changed or (not change and obj.stage == "quoted"):
            from .services import move_stage
            move_stage(obj, obj.stage, request.user)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("subject", "kind", "partner", "opportunity", "due_date", "done", "owner")
    list_filter = ("kind", "done", "owner")
    search_fields = ("subject", "partner__name", "notes")
    autocomplete_fields = ["partner"]


from .models import Campaign, CampaignRecipient  # noqa: E402


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    readonly_fields = ("partner", "to", "status")
    can_delete = False


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "status", "queued", "skipped", "sent_at")
    list_filter = ("channel", "status")
    readonly_fields = ("status", "sent_at", "sent_by", "queued", "skipped")
    inlines = [CampaignRecipientInline]
