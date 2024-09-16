from rest_framework import serializers
from django.db import models
from django.contrib.auth.models import User

class LearningData(models.Model):
    data = models.BinaryField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    def __str__(self):
        return f"Learning Data for {self.user.username}"