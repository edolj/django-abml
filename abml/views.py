from .utils.main import learningRules, criticalInstances, getCounterExamples

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

# Create your views here.
# takes request -> returns response
def learning_rules_api(request):
    rules = learningRules(request.user)
    return JsonResponse({'rules': rules})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def critical_instances(request):
    critical_instances_data = criticalInstances(request.user)
    return JsonResponse({'critical_instances': critical_instances_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def counter_examples(request):
    if request.method == 'POST':
        try:
            # Extract JSON data from the request body
            data = json.loads(request.body)
            
            # Access the data fields
            index = data.get('index')
            user_argument = data.get('userArgument')

            counterExamples, bestRule, m_score = getCounterExamples(index, user_argument, request.user)
            if "error" in counterExamples:
                return JsonResponse({'error': counterExamples["error"]}, status=400)
            else:
                return JsonResponse({'counterExamples': counterExamples, 'bestRule': bestRule, 'm_score': m_score})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return JsonResponse({'error': 'Please provide all required fields.'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists.'}, status=400)

        User.objects.create_user(username=username, password=password)
        return JsonResponse({'message': 'User created successfully.'}, status=201)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
    except (AttributeError, Token.DoesNotExist):
        pass
    return Response(status=204)
