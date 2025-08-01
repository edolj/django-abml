#!/usr/bin/env python
# -*- coding: utf-8 -*- 
__author__ = 'edo'

import re, pickle
from Orange.data import Table, Domain as OrangeDomain, ContinuousVariable
from Orange.classification.rules import Rule, Selector
from .backend.orange3_abml_master.orangecontrib.abml import abrules, argumentation
from .backend.orange3_evcrules_master.orangecontrib.evcrules.rules import MEstimateEvaluator
from ..models import LearningData, Domain

_learner_cache = {}

def get_user_id(user):
    return user.id if hasattr(user, "id") else user["id"]

def get_learner(user, sessionId):
    key = (get_user_id(user), sessionId)
    if key not in _learner_cache:
        _learner_cache[key] = abrules.ABRuleLearner()
    return _learner_cache[key]

def addArgument(learning_data, row_index, user_argument, full_data, user, sessionId):
    # Find the index of the "Arguments" column in the metas
    arguments_index = next((i for i, meta in enumerate(learning_data.domain.metas) if meta.name == "Arguments"), None)
    
    if arguments_index is None:
        print("Error: 'Arguments' meta attribute not found.")
        return False

    # Update the value in the "Arguments" column for the specified row
    learning_data[row_index].metas[arguments_index] = user_argument
    full_data[row_index].metas[arguments_index] = user_argument

    serialized_data = serialize_table(full_data)
    LearningData.objects.update_or_create(
        user=user,
        session_id = sessionId,
        defaults={'full_data': serialized_data}
    )

def setLearningData(user, domain_name):
    try:
        domain = Domain.objects.get(name=domain_name)
    except Domain.DoesNotExist:
        print(f"Domain '{domain_name}' not found.")
        return None

    if not domain.data:
        print(f"No data found for domain '{domain_name}'")
        return None
    
    table = pickle.loads(domain.data)
    serialized_data = serialize_table(table)
    expert_attributes = domain.expert_attributes or []
    inactive_attributes = expert_attributes.copy()
    display_names = domain.display_names
    attr_descriptions = domain.attr_descriptions
    attr_tooltips = domain.attr_tooltips

    learning_data_instance = LearningData.objects.create(
        user=user,
        data=serialized_data, 
        iteration=0, 
        name=domain_name,
        full_data=serialized_data,
        inactive_attributes=inactive_attributes,
        expert_attributes=expert_attributes,
        display_names=display_names,
        attr_descriptions=attr_descriptions,
        attr_tooltips=attr_tooltips
    )

    return learning_data_instance

def getLearningData(user, sessionId):
    # Retrieve the user's LearningData entry
    try:
        learning_data_entry = LearningData.objects.get(user=user, session_id=sessionId)
    except LearningData.DoesNotExist:
        return None, None
    
    # Deserialize the data
    full_data = deserialize_table(learning_data_entry.full_data)
    inactive_attrs = learning_data_entry.inactive_attributes or []
    active_data = remove_inactive_attributes(full_data, inactive_attrs)
    return active_data, full_data

def getInactiveAttr(user, sessionId):
    try:
        learning_data_entry = LearningData.objects.get(user=user, session_id=sessionId)
        return learning_data_entry.inactive_attributes or []
    except LearningData.DoesNotExist:
        return []
    
def getExpertAttr(user, sessionId):
    try:
        learning_data_entry = LearningData.objects.get(user=user, session_id=sessionId)
        return learning_data_entry.expert_attributes or []
    except LearningData.DoesNotExist:
        return []
    
def getDisplayNameAttr(user, sessionId):
    try:
        learning_data_entry = LearningData.objects.get(user=user, session_id=sessionId)
        return learning_data_entry.display_names or {}
    except LearningData.DoesNotExist:
        return {}
    
def setIteration(user, sessionId):
    try:
        learning_data_entry = LearningData.objects.get(user=user, session_id=sessionId)
        current_iteration = learning_data_entry.iteration
        learning_data_entry.iteration = current_iteration + 1
        learning_data_entry.save()
    except LearningData.DoesNotExist:
        print("No data found")

def getIteration(user, sessionId):
    try:
        learning_data_entry = LearningData.objects.get(user=user, session_id=sessionId)
        return learning_data_entry.iteration
    except LearningData.DoesNotExist:
        return 0

def serialize_table(table):
    return pickle.dumps(table)

def deserialize_table(data):
    return pickle.loads(data)

def update_table_database(data, user, sessionId, user_argument, full_data):
    inactive_attrs = getInactiveAttr(user, sessionId)
    extracted_attrs = extract_attributes(user_argument)
    for attr in extracted_attrs:
        if attr in inactive_attrs:
            inactive_attrs.remove(attr)
            data = add_attribute_back(full_data, data, attr)
            
    # Serialize the updated Table object
    serialized_data = serialize_table(data)
    
    # Update the database entry
    LearningData.objects.update_or_create(
        user=user,
        session_id = sessionId,
        defaults={'data': serialized_data, 'inactive_attributes': inactive_attrs}
    )

def remove_inactive_attributes(data, inactive_attrs):
    active_attrs = [a for a in data.domain.attributes if a.name not in inactive_attrs]
    domain = OrangeDomain(active_attrs, data.domain.class_var, data.domain.metas)
    return Table.from_table(domain, data)

def add_attribute_back(full_data, current_data, attr_name):
    current_attr_names = [a.name for a in current_data.domain.attributes]
    new_attrs = [a for a in full_data.domain.attributes if a.name in current_attr_names or a.name == attr_name]
    domain = OrangeDomain(new_attrs, full_data.domain.class_var, full_data.domain.metas)
    return Table.from_table(domain, full_data)

def extract_attributes(input_str):
    pattern = r'([\w./]+)\s*(?:<=|>=|=|<|>)?'
    return re.findall(pattern, input_str)

# http://localhost:8000/api/get-charts-data/
def gatherDataToVisualize(user, sessionId):
    _, full_data = getLearningData(user, sessionId)

    result = {}
    for attr in full_data.domain.attributes:
        if isinstance(attr, ContinuousVariable):
            values = [row[attr.name] for row in full_data]
            result[attr.name] = values
    
    return result

# http://localhost:8000/api/learning-rules/
def learningRules(user, sessionId):
    learning_data, _ = getLearningData(user, sessionId)
    learner = get_learner(user, sessionId)
    classifier = learner(learning_data)
    
    # Collect data into a list of dictionaries
    rules_data = []
    for rule in classifier.rule_list:
        rule_data = {
            'curr_class_dist': rule.curr_class_dist.tolist(),
            'rule': str(rule),
            'quality': rule.quality
        }
        rules_data.append(rule_data)
    
    return rules_data

# http://localhost:8000/api/attributes/
def getAttributes(user, sessionId):
    _, learning_data = getLearningData(user, sessionId)
    domain = learning_data.domain
    target_name = domain.class_var.name if domain.class_var else None
    meta_names = {var.name for var in domain.metas}

    attributes_list = []
    for attribute in domain:
        if attribute.name == target_name:
            attr_type = "target"
        elif attribute.name in meta_names:
            attr_type = "meta"
        elif attribute.is_continuous:
            attr_type = "continuous"
        elif attribute.is_discrete:
            attr_type = "discrete"
        else:
            attr_type = "unknown"

        attributes_list.append({
            "name": attribute.name,
            "type": attr_type
        })

    return attributes_list

def get_categorical_and_numerical_attributes(domain):
    categorical_and_numerical_attributes = []
    for attribute in domain:
        if attribute.is_continuous or attribute.is_discrete:
            categorical_and_numerical_attributes.append(str(attribute))
    return categorical_and_numerical_attributes

# http://localhost:8000/api/critical-instances/
def criticalInstances(user, domain_name, startNewSession=False, sessionId=None):
    if startNewSession or sessionId is None:
        learning_data_entry = setLearningData(user, domain_name)
        if learning_data_entry is None: 
            return None, None
        sessionId = learning_data_entry.session_id

    learning_data, full_data = getLearningData(user, sessionId)
    if learning_data is None:
        learning_data_entry = setLearningData(user, domain_name)
        if learning_data_entry is None:
            return None, None
        sessionId = learning_data_entry.session_id
        learning_data, full_data = getLearningData(user, sessionId)

    learner = get_learner(user, sessionId)
    _ = learner(learning_data)
    iteration = getIteration(user, sessionId)
    
    target_class = learning_data.domain.class_var.name if learning_data.domain.class_var else None
    crit_ind, problematic, problematic_rules = argumentation.find_critical(learner, learning_data)

    # Extract the critical example from the original dataset
    if iteration < 3:
        selected_indices = crit_ind[-5:]
        selected_problematic = problematic[-5:]
        selected_instances = learning_data[selected_indices]
    else:
        selected_indices = crit_ind[:5]
        selected_problematic = problematic[:5]
        selected_instances = learning_data[selected_indices]

    domains = get_categorical_and_numerical_attributes(full_data.domain)

    pairs = []
    detail_data = []
    for index in selected_indices:
        instance = full_data[index]
        for d in domains:
            pairs.append((d, str(instance[d])))
        detail_data.append(pairs)
        pairs = []
    
    critical_instances_list = []
    for index, instance in enumerate(selected_instances):
        critical_instances_list.append({
            "critical_index": str(selected_indices[index]),
            "problematic": str(round(selected_problematic[index], 3)),
            "target_class": str(instance[target_class]),
            "id": str(instance["id"])
        })
    return critical_instances_list, detail_data

# http://localhost:8000/api/counter-examples/
def getCounterExamples(critical_index, user_argument, user, sessionId):
    learning_data, full_data = getLearningData(user, sessionId)

    # change it to format {argument}
    formatedArg = "{{{}}}".format(user_argument)
    # add argument to argument column in row critical_index
    if addArgument(learning_data, int(critical_index), formatedArg, full_data, user, sessionId) == False:
        return {"error": "Failed to add argument to column. Please try again."}, "", "", ""
    
    update_table_database(learning_data, user, sessionId, user_argument, full_data)
    learning_data, full_data = getLearningData(user, sessionId)
    
    learner = get_learner(user, sessionId)
    try:
        arg_rule, counters, best_rule = argumentation.analyze_argument(learner, learning_data, int(critical_index))
        arg_m_score = learner.evaluator_norm.evaluate_rule(arg_rule)
        best_m_score = learner.evaluator_norm.evaluate_rule(best_rule)

        if arg_m_score > best_m_score:
            best_rule = arg_rule
            
    except ValueError as e:
        return {"error": "Something went wrong with analyzing arguments.. " + str(e)}, "", "", ""
    
    counter_examples = []
    if counters:
        counterEx = full_data[list(counters)]
        domains = get_categorical_and_numerical_attributes(full_data.domain)

        for counter in counterEx:
            counter_id = str(counter["id"]) if "id" in counter.domain else "Unknown"
            values = [str(counter[d]) for d in domains]
            counter_examples.append({
                "id": counter_id,
                "values": values
            })

    return counter_examples, str(best_rule), arg_m_score, best_m_score

def main():
    """
    Main function, which contains the ABML interactive loop.
    """

    """
    path = os.getcwd() + "/backend/orange3_abml_master/orangecontrib/abml/data/"
    file_path = path + "bonitete_tutor.tab"

    learning_data = Table(file_path)
    learner = abrules.ABRuleLearner()

    input("Ready to learn? Press enter")

    # MAIN LOOP
    while True:
        print("Learning rules...")

        learner.calculate_evds(learning_data)
        classifier = learner(learning_data)

        # print learned rules
        for rule in classifier.rule_list:
            print(rule.curr_class_dist.tolist(), rule, rule.quality)
        print()

        print("Finding critical examples...")
        crit_ind, problematic, problematic_rules = argumentation.find_critical(learner, learning_data)

        # Extract the critical example from the original dataset
        critical_instances = learning_data[crit_ind]
        print("Critical instances:")
        for index, instance in enumerate(critical_instances[:5]):
            print(index+1, " -> ", instance["credit.score"], " ", instance["activity.ime"], " ", problematic[:5][index])
            
        # show user 5 critical examples and let him choose
        while True:
            selectedInstanceIndex = input("Choose critical example (number between 1 and 5): ")
    
            # Check if the input is not a number or not in the specified range
            if not selectedInstanceIndex.isdigit() or int(selectedInstanceIndex) not in range(1, 6):
                print("Invalid input. Please choose critical instance between 1 and 5.")
                continue
            else:
                break
        
        # selected index is now critical_index
        critical_index = crit_ind[:5][int(selectedInstanceIndex) - 1]

        while True:
            # input argument
            print("Argument input...")

            while True:
                # take input as argument
                user_argument = input("Enter argument: ")

                if user_argument in learning_data.domain:
                    break
                else:
                    print("Wrong argument")
            
            getIndex = learning_data.domain.index(user_argument)
            attribute = learning_data.domain[getIndex]
            if attribute.is_continuous:
                while True:
                    sign = input("Enter >= or <= : ")
                    if sign == ">=" or sign == "<=":
                        user_argument += sign
                        break

            # change it to format {argument}
            formatedArg = "{{{}}}".format(user_argument)
            # add argument to "Arguments" column in row critical_index
            addArgument(learning_data, critical_index, formatedArg)
            learner.calculate_evds(learning_data)

            input("Press enter for argument analysis")

            print("Analysing argument...")
            counters, counters_vals, rule, prune, best_rule = argumentation.analyze_argument(learner, learning_data, critical_index)
            
            if len(counters) > 0:
                counter_examples = learning_data[list(counters)]
                print("Counter examples:")
                for counterEx in counter_examples:
                    print(counterEx)
            else:
                print("No counter examples found for the analyzed example.")

            while True:
                inp = input("(c)hange argument, (d)one with argumentation (new critical): ")
                if inp in ('c', 'd'):
                    break
            if inp == 'c':
                removeArgument(learning_data, critical_index)
            if inp == 'd':
                # show which critical example was done in this iteration
                critical_instance = learning_data[critical_index]
                print("This iteration critical example:", critical_instance)
                break

        # increment iteration
        print("Next iteration:")
        """

    return 0

if __name__ == '__main__':
    status = main()