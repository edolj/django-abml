from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .utils.main import learningRules, criticalInstances, getCounterExamples
import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# Create your views here.
# takes request -> returns response
def learning_rules_api(request):
    rules = learningRules()
    return JsonResponse({'rules': rules})

def critical_instances(request):
    critical_instances_data = criticalInstances()
    return JsonResponse({'critical_instances': critical_instances_data})

@api_view(['POST'])
@permission_classes([AllowAny])
def counter_examples(request):
    if request.method == 'POST':
        try:
            # Extract JSON data from the request body
            data = json.loads(request.body)
            
            # Access the data fields
            index = data.get('index')
            user_argument = data.get('userArgument')

            counterExamples, bestRule = getCounterExamples(index, user_argument)
            if "error" in counterExamples:
                return JsonResponse({'error': counterExamples["error"]}, status=400)
            else:
                return JsonResponse({'counterExamples': counterExamples, 'bestRule': bestRule})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)