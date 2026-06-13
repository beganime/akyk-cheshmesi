from rest_framework import serializers

from .models import CompanyTeamMember, SiteSettings, SupportRequest


class SiteSettingsSerializer(serializers.ModelSerializer):
    logo_file_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            "uuid",
            "company_name",
            "legal_company_name",
            "director_name",
            "logo_url",
            "logo_file_url",
            "hero_title",
            "hero_subtitle",
            "about_company",
            "translation_company_text",
            "students_life_text",
            "security_text",
            "privacy_policy",
            "terms_of_use",
            "google_play_url",
            "testflight_url",
            "contact_email",
            "contact_phone",
            "support_email",
            "updated_at",
        )

    def get_logo_file_url(self, obj: SiteSettings) -> str:
        if not obj.logo:
            return ""
        request = self.context.get("request")
        url = obj.logo.url
        return request.build_absolute_uri(url) if request else url


class CompanyTeamMemberSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    team_label = serializers.CharField(source="get_team_display", read_only=True)

    class Meta:
        model = CompanyTeamMember
        fields = (
            "uuid",
            "full_name",
            "role",
            "team",
            "team_label",
            "bio",
            "photo_url",
            "email",
            "telegram",
            "display_order",
        )

    def get_photo_url(self, obj: CompanyTeamMember) -> str:
        if not obj.photo:
            return ""
        request = self.context.get("request")
        url = obj.photo.url
        return request.build_absolute_uri(url) if request else url


class SupportRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportRequest
        fields = ("uuid", "full_name", "email", "phone", "preferred_contact", "topic", "message", "created_at")
        read_only_fields = ("uuid", "created_at")

    def validate(self, attrs):
        email = attrs.get("email", "").strip()
        phone = attrs.get("phone", "").strip()
        if not email and not phone:
            raise serializers.ValidationError("Укажите email или телефон для обратной связи.")
        return attrs
