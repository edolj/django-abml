from django.db import models
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

class LearningData(models.Model):
    data = models.BinaryField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    iteration = models.IntegerField(default=0)
    full_data = models.BinaryField(null=True)
    inactive_attributes = ArrayField(models.CharField(max_length=50), default=list, blank=True)

    def __str__(self):
        return f"Learning Data for {self.user.username}"
    
class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)
    data = models.BinaryField()

    def __str__(self):
        return self.name
    
class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'name']
    
class RegisterSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user