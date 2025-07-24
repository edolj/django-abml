from .utils.main import learningRules, criticalInstances, getCounterExamples
from .utils.main import setIteration, getIteration, gatherDataToVisualize
from .utils.main import getAttributes, getExpertAttr, getDisplayNameAttr

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Domain, LearningData
from .models import RegisterSerializer, DomainSerializer
from .models import LearningDataSerializer, LearningIterationSerializer

from Orange.data import Table
import pickle, tempfile, os

# Create your views here.
# takes request -> returns response
def learning_rules_api(request):
    rules = learningRules(request.user)
    return JsonResponse({'rules': rules})

@api_view(['POST'])
def critical_instances(request):
    domain_name = request.data.get("domain")
    start_new = request.data.get("startNew")
    critical_instances_data = criticalInstances(request.user, domain_name, startNewSession=start_new)
    if critical_instances_data is None:
        return JsonResponse({'error': 'Failed to initialize learning data.'}, status=status.HTTP_400_BAD_REQUEST)
    return JsonResponse({'critical_instances': critical_instances_data})

@api_view(['POST'])
def counter_examples(request):
    try:
        data = request.data
        index = data.get('index')
        user_argument = data.get('userArgument')

        counterExamples, bestRule, arg_m_score, best_m_score = getCounterExamples(index, user_argument, request.user)
        if "error" in counterExamples:
            return Response({'error': counterExamples["error"]}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'counterExamples': counterExamples, 'bestRule': bestRule,
                             'arg_m_score': arg_m_score, 'best_m_score': best_m_score})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
def get_iteration_number(request):
    iterationNumber = getIteration(request.user)
    return JsonResponse({'iterationNumber': iterationNumber})

@api_view(['PUT'])
def set_iteration_number(request):
    setIteration(request.user)
    return JsonResponse({'message': 'Iteration updated successfully'}, status=200)

@api_view(['POST'])
def create_learning_iteration(request):
    data = request.data
    try:
        learning_data = LearningData.objects.get(user=request.user)
    except LearningData.DoesNotExist:
        return Response({"error": "LearningData not found"}, status=404)

    serializer = LearningIterationSerializer(data={
        "learning_data": learning_data.id,
        "iteration_number": data.get("iteration_number"),
        "chosen_arguments": data.get("chosen_arguments"),
    })

    if serializer.is_valid():
        serializer.save(learning_data=learning_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_learning_iterations(request):
    all_data = LearningData.objects.all().select_related('user').prefetch_related('iterations')
    result = []

    for ld in all_data:
        iterations = ld.iterations.all().order_by('iteration_number')
        serializer = LearningIterationSerializer(iterations, many=True)
        result.append({
            "username": ld.user.username,
            "domain_name": ld.name,
            "iterations": serializer.data,
        })

    return Response(result)
    
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

@api_view(['GET'])
def get_domains(request):
    domains = Domain.objects.all()
    serializer = DomainSerializer(domains, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_attributes(request):
    attributes = getAttributes(request.user)
    return Response(attributes)

@api_view(['GET'])
def get_expert_attributes(request):
    attributes = getExpertAttr(request.user)
    return Response(attributes)

@api_view(['GET'])
def get_display_names(request):
    attributes = getDisplayNameAttr(request.user)
    return Response(attributes)

@api_view(['GET'])
def get_learning_object(request):
    try:
        learning_data = LearningData.objects.get(user=request.user)
    except LearningData.DoesNotExist:
        return Response({})

    serializer = LearningDataSerializer(learning_data)
    return Response(serializer.data)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_domain(request):
    file = request.FILES.get('file')
    name = request.POST.get('name')

    if not file or not name:
        return Response({'error': 'Missing file or name'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Domain.objects.filter(name=name).exists():
        return Response({'error': 'Domain with this name already exists.'}, status=400)

    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tab") as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        table = Table(temp_file_path)
        binary_data = pickle.dumps(table)
        all_attrs = list(table.domain.attributes) + list(table.domain.metas)
        if table.domain.class_var is not None:
            all_attrs.append(table.domain.class_var)
        attribute_names = [attr.name for attr in all_attrs]
        display_names = {attr.name: attr.name for attr in all_attrs}
        attr_descriptions = {attr.name: "" for attr in all_attrs}
        attr_tooltips = {attr.name: "" for attr in all_attrs}

        # Save to DB
        Domain.objects.create(name=name, 
                              data=binary_data, 
                              attributes=attribute_names, 
                              expert_attributes=[],
                              display_names=display_names,
                              attr_descriptions=attr_descriptions,
                              attr_tooltips=attr_tooltips)

        # Return the response with the serialized domain
        serializer = DomainSerializer(Domain.objects.get(name=name))
        return Response(serializer.data, status=201)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    finally:
        # Ensure cleanup of the temporary file after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@api_view(['DELETE'])
def delete_domain(request, domain_id):
    try:
        domain = Domain.objects.get(id=domain_id)
        domain.delete()
        return Response({'message': 'Domain deleted successfully.'}, status=204)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found.'}, status=404)
    
@api_view(['PUT'])
def update_domain(request, domain_id):
    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

    expert_attributes = request.data.get('expert_attributes')
    display_names = request.data.get('display_names')
    attr_descriptions = request.data.get('attr_descriptions')
    attr_tooltips = request.data.get('attr_tooltips')

    if expert_attributes is not None:
        domain.expert_attributes = expert_attributes

    if display_names is not None:
        domain.display_names = display_names

    if attr_descriptions is not None:
        domain.attr_descriptions = attr_descriptions

    if attr_tooltips is not None:
        domain.attr_tooltips = attr_tooltips

    domain.save()

    return Response({'message': 'Domain updated successfully'})

@api_view(['GET'])
def get_all_numeric_attributes(request):
    result = gatherDataToVisualize(request.user)
    return JsonResponse(result)
