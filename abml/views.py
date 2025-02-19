from .utils.main import learningRules, criticalInstances, getCounterExamples

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import RegisterSerializer

# Create your views here.
# takes request -> returns response
def learning_rules_api(request):
    rules = learningRules(request.user)
    return JsonResponse({'rules': rules})

@api_view(['GET'])
def critical_instances(request):
    critical_instances_data = criticalInstances(request.user)
    return JsonResponse({'critical_instances': critical_instances_data})

@api_view(['POST'])
def counter_examples(request):
    try:
        data = request.data
        index = data.get('index')
        user_argument = data.get('userArgument')

        counterExamples, bestRule, m_score = getCounterExamples(index, user_argument, request.user)
        if "error" in counterExamples:
            return Response({'error': counterExamples["error"]}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'counterExamples': counterExamples, 'bestRule': bestRule, 'm_score': m_score})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({'message': 'Registration successful!'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)  # Start session
        return JsonResponse({"message": "Login successful", "user": {"id": user.id, "username": user.username}}, status=200)
    else:
        return JsonResponse({"error": "Invalid credentials"}, status=400)

@api_view(['POST'])
def logout_view(request):
    logout(request)  # Clear session
    return JsonResponse({"message": "Logged out successfully"}, status=200)

@api_view(['GET'])
def check_session(request):
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "username": request.user.username})
    return JsonResponse({"authenticated": False}, status=401)

@api_view(['GET'])
def get_users(request):
    users = User.objects.filter(is_superuser=False).values('id', 'username', 'first_name', 'last_name', 'email')
    return JsonResponse(list(users), safe=False)