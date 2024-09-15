from rest_framework import serializers
from django.db import models

class LearningData(models.Model):
    data = models.BinaryField()