from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password

from .models import PortalAccess


class PortalUserForm(forms.ModelForm):
    username = forms.CharField(label="Kullanıcı adı", help_text="Bayinin giriş yapacağı kullanıcı adı (Türkçe karakter kullanmayın).")
    email = forms.EmailField(label="E-posta", required=False)
    password = forms.CharField(label="İlk şifre", widget=forms.PasswordInput, help_text="En az 10 karakter. Bayiye güvenli yoldan iletin.")

    class Meta:
        model = PortalAccess
        fields = ["partner", "active"]

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username=u).exists():
            raise forms.ValidationError("Bu kullanıcı adı kullanılıyor.")
        return u

    def clean_password(self):
        validate_password(self.cleaned_data["password"])
        return self.cleaned_data["password"]


@admin.register(PortalAccess)
class PortalAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "partner", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("user__username", "partner__name")
    autocomplete_fields = ["partner"]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = PortalUserForm
        return super().get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        return ["user"] if obj else []

    def save_model(self, request, obj, form, change):
        if not change:
            user = get_user_model().objects.create_user(form.cleaned_data["username"], form.cleaned_data.get("email", ""),
                                                        form.cleaned_data["password"], is_staff=False)
            user.groups.add(Group.objects.get_or_create(name="Bayi")[0])
            obj.user = user
            messages.info(request, f"Bayi giriş adresi: /portal/ — kullanıcı: {user.username}")
        super().save_model(request, obj, form, change)
