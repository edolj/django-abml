from django.db import models
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
import uuid

class LearningData(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    data = models.BinaryField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    iteration = models.IntegerField(default=0)
    name = models.CharField(max_length=255, default="")
    full_data = models.BinaryField(null=True)
    inactive_attributes = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    expert_attributes = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    display_names = models.JSONField(default=dict, blank=True)
    attr_descriptions = models.JSONField(default=dict, blank=True)
    attr_tooltips = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Learning Data for {self.user.username}"
    
class LearningDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningData
        fields = ['session_id', 'name', 'iteration', 'inactive_attributes', 'expert_attributes', 
                  'display_names', 'attr_descriptions', 'attr_tooltips', 'created_at']
        
class LearningIteration(models.Model):
    learning_data = models.ForeignKey(LearningData, on_delete=models.CASCADE, related_name='iterations')
    selectedExampleId = models.CharField(default="")
    iteration_number = models.IntegerField()
    chosen_arguments = ArrayField(models.CharField(max_length=100))
    mScore = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.learning_data.user.username} - Iteration {self.iteration_number}"

class LearningIterationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningIteration
        fields = ['selectedExampleId', 'iteration_number', 'chosen_arguments', 'mScore', 'timestamp']

class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)
    data = models.BinaryField()
    attributes = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    expert_attributes = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    display_names = models.JSONField(default=dict, blank=True)
    attr_descriptions = models.JSONField(default=dict, blank=True)
    attr_tooltips = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name
    
class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'name', 'attributes', 'expert_attributes',
                   'display_names', 'attr_descriptions', 'attr_tooltips']
    
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

class SkillKnowledge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    learning_data = models.ForeignKey(LearningData, on_delete=models.CASCADE)
    attribute = models.CharField(max_length=100)

    P_L = models.FloatField(default=0.1)
    P_T = models.FloatField(default=0.2)
    P_G = models.FloatField(default=0.15)
    P_S = models.FloatField(default=0.1)

    class Meta:
        unique_together = ('user', 'learning_data', 'attribute')

class SkillKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillKnowledge
        fields = ['attribute', 'P_L']