from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .utils.main import learningRules, criticalInstances, getCriticalExamples
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
        # Extract JSON data from the request body
        try:
            data = json.loads(request.body)
            # Access the data fields
            index = data.get('index')
            user_argument = data.get('userArgument')
            high_low = data.get('highLow')

            counterExamples = getCriticalExamples(index, user_argument, high_low)
            if "error" in counterExamples:
                return JsonResponse({'error': counterExamples["error"]}, status=400)
            elif "message" in counterExamples:
                return JsonResponse({'message': counterExamples["message"]})
            else:
                return JsonResponse({'counterExamples': counterExamples})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)