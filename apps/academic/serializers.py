"""Serializers del módulo."""

from rest_framework import serializers

from apps.academic.models import AcademicPeriod, Course, GradeRecord


class AcademicPeriodSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = AcademicPeriod
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CourseSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class GradeRecordSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = GradeRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
