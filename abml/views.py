from .utils.main import learningRules, criticalInstances, getCounterExamples
from .utils.main import setIteration, getIteration, gatherDataToVisualize
from .utils.main import getAttributes, getExpertAttr, getDisplayNameAttr
from .utils.main import saveArgumentToDatabase

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Domain, DomainSerializer, RegisterSerializer
from .models import LearningData, LearningDataSerializer, LearningIterationSerializer
from .models import SkillKnowledge, SkillKnowledgeSerializer

from Orange.data import Table
import pickle, tempfile, os
from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_current_session_id(user):
    learning_data = LearningData.objects.filter(user=user).order_by('-created_at').first()
    if not learning_data:
        return None
    return learning_data.session_id

# Create your views here.
# takes request -> returns response
def learning_rules_api(request):
    sessionId = get_current_session_id(request.user)
    rules = learningRules(request.user, sessionId)
    return JsonResponse({'rules': rules})

@api_view(['POST'])
def critical_instances(request):
    domain_name = request.data.get("domain")
    start_new = request.data.get("startNew")
    sessionId = get_current_session_id(request.user)
    critical_instances_data = criticalInstances(request.user, domain_name, 
                                                startNewSession=start_new, 
                                                sessionId = sessionId)
    if critical_instances_data is None:
        return JsonResponse({'error': 'Failed to initialize learning data.'}, status=status.HTTP_400_BAD_REQUEST)
    return JsonResponse({'critical_instances': critical_instances_data})

@api_view(['POST'])
def counter_examples(request):
    try:
        data = request.data
        index = data.get('index')
        user_argument = data.get('userArgument')
        sessionId = get_current_session_id(request.user)

        counterExamples, argRule, bestRule, arg_m_score, best_m_score = getCounterExamples(
            index, user_argument, request.user, sessionId
        )

        if isinstance(counterExamples, dict) and "error" in counterExamples:
            return Response({'error': counterExamples["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'counterExamples': counterExamples,
            'argRule': argRule,
            'bestRule': bestRule,
            'arg_m_score': arg_m_score,
            'best_m_score': best_m_score
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
def get_iteration_number(request):
    sessionId = get_current_session_id(request.user)
    iterationNumber = getIteration(request.user, sessionId)
    return JsonResponse({'iterationNumber': iterationNumber})

@api_view(['PUT'])
def set_iteration_number(request):
    sessionId = get_current_session_id(request.user)
    setIteration(request.user, sessionId)
    return JsonResponse({'message': 'Iteration updated successfully'}, status=200)

@api_view(['POST'])
def create_learning_iteration(request):
    data = request.data
    learning_data = LearningData.objects.filter(user=request.user).order_by('-created_at').first()
    if not learning_data:
        return Response({"error": "LearningData not found"}, status=404)

    critical_index = int(data.get("index"))
    user_argument = data.get("chosen_arguments")
    sessionId = get_current_session_id(request.user)
    saveArgumentToDatabase(critical_index, user_argument, request.user, sessionId)

    serializer = LearningIterationSerializer(data={
        "learning_data": learning_data.id,
        "selectedExampleId": data.get("selectedExampleId", ""),
        "iteration_number": data.get("iteration_number"),
        "chosen_arguments": data.get("chosen_arguments"),
        "mScore": data.get("mScore", 0.0),
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
        return JsonResponse({"authenticated": True, 
                             "username": request.user.username,
                             "is_superuser": request.user.is_superuser})
    return JsonResponse({"authenticated": False}, status=401)

@api_view(['GET'])
def get_users(request):
    users = User.objects.filter(is_superuser=False).order_by('id').values('id', 'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login', 'is_active', 'is_superuser')
    return JsonResponse(list(users), safe=False)

@api_view(['GET'])
def get_domains(request):
    domains = Domain.objects.all()
    serializer = DomainSerializer(domains, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_attributes(request):
    sessionId = get_current_session_id(request.user)
    attributes = getAttributes(request.user, sessionId)
    return Response(attributes)

@api_view(['GET'])
def get_expert_attributes(request):
    sessionId = get_current_session_id(request.user)
    attributes = getExpertAttr(request.user, sessionId)
    return Response(attributes)

@api_view(['GET'])
def get_display_names(request):
    sessionId = get_current_session_id(request.user)
    attributes = getDisplayNameAttr(request.user, sessionId)
    return Response(attributes)

@api_view(['GET'])
def get_learning_object(request):
    learning_data = LearningData.objects.filter(user=request.user).order_by('-created_at').first()
    if not learning_data:
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
    sessionId = get_current_session_id(request.user)
    result = gatherDataToVisualize(request.user, sessionId)
    return JsonResponse(result)

@api_view(['GET'])
def get_skill_knowledge(request):
    try:
        user = request.user
        sessionId = get_current_session_id(user)
        learning_data = LearningData.objects.get(user=user, session_id=sessionId)
        skills = SkillKnowledge.objects.filter(user=user, learning_data=learning_data)

        serializer = SkillKnowledgeSerializer(skills, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
def get_summary(request):
    data = request.data
    
    domainName = data.get('domainName', '')
    details = data.get('details', {})
    display_names = data.get('displayNames', {})
    target_class = data.get('targetClass', '')
    arg_rule = data.get('argRule', '')
    user_arguments = data.get('user_arguments', [])
    
    readable_arguments = []
    for arg in user_arguments:
        display_name = arg.get("displayName") or arg.get("key", "Unknown attribute")
        readable_arguments.append(f"- {display_name}")
    readable_arguments_text = "\n".join(readable_arguments)

    system_message = {
        "role": "system",
        "content": (
            "You are a tutor in an argument-based learning system. "
            "Provide a short summary for the learner. "
            "Explain clearly and simply:\n"
            f"- Why the example was classified as it was.\n"
            f"- How the selected arguments:\n{readable_arguments_text}\nsupport this classification.\n"
            "- What the learner should take away from this step (the key insight).\n"
            "Avoid technical jargon, keep it brief (3-4 sentences), and focus on helping the learner understand."
        )
    }

    user_message = {
        "role": "user",
        "content": (
            f"In the domain '{domainName}' learner is exploring how examples are classified.\n\n"
            f"This example is classified as: {target_class}\n\n"
            "Example details:\n" +
            "\n".join([f"- {display_names.get(attr, attr)}: {val}" for attr, val in details]) + "\n\n"
            f"The learner selected arguments to explain the classification:\n{readable_arguments_text}\n\n"
            f"Rule generated by the algorithm based on selected arguments:\n{arg_rule}\n\n"
            "Please summarize what the student learned in this iteration. "
            "Focus on how the selected arguments support the classification and what key concept or insight was gained. "
            "Avoid unnecessary numbers or technical terms. Keep the summary to 3-4 sentences."
        )
    }

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[system_message, user_message],
        )
        summary = response.choices[0].message.content
        return Response({"summary": summary})

    except Exception as e:
        return Response({"error": str(e)}, status=500)

