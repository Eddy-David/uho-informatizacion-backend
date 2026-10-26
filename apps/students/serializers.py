"""Serializers del módulo."""

from rest_framework import serializers

from apps.students.models import Enrollment, StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = StudentProfile
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = Enrollment
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
