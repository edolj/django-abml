#!/usr/bin/env python
# -*- coding: utf-8 -*- 
__author__ = 'edo'

import os, json
from Orange.data import Table
from Orange.classification.rules import Rule, Selector
from .backend.orange3_abml_master.orangecontrib.abml import abrules, argumentation

def stars_with_header(msg):
    """
    Util function for prettier output.
    """
    stars = 70
    txt = "*" * stars + "\n"
    txt += msg
    print(txt)
    return

def addArgumentToColumn(row_index, argument_to_add):
    path = os.getcwd() + "/abml/utils/"
    file_path = path + "bonitete_tutor.tab"

    # Read the contents of the .tab file
    with open(file_path, "r") as file:
        rows = file.readlines()

    # Check if the row index is within the range of rows
    if 0 <= row_index < len(rows):
        # Split the row into columns using tab as delimiter
        columns = rows[row_index].rstrip().split('\t')

        # Add the string to the last column
        columns.append(argument_to_add)

        # Join the columns back into a row with tabs as delimiter
        updated_row = '\t'.join(columns) + '\n'

        # Update the specific row in the rows list
        rows[row_index] = updated_row

        # Write the updated contents back to the .tab file
        with open(file_path, "w") as file:
            file.writelines(rows)
    else:
        print("Row index out of range.")

def removeArgumentFromColumn(row_index):
    path = os.getcwd() + "/abml/utils/"
    file_path = path + "bonitete_tutor.tab"

    # Read the contents of the .tab file
    with open(file_path, "r") as file:
        rows = file.readlines()

    # Check if the row index is within the range of rows
    if 0 <= row_index < len(rows):
        # Split the row into columns using tab as delimiter
        columns = rows[row_index].rstrip().split('\t')

        # Check if there are arguments to remove
        if len(columns) > 1:
            # Remove the last argument
            columns.pop()

            # Join the columns back into a row with tabs as delimiter
            updated_row = '\t'.join(columns) + '\n'

            # Update the specific row in the rows list
            rows[row_index] = updated_row

            # Write the updated contents back to the .tab file
            with open(file_path, "w") as file:
                file.writelines(rows)
        else:
            print("No argument to remove from the specified row.")
    else:
        print("Row index out of range.")
        
def learnerAndLearningData():
    path = os.getcwd() + "/abml/utils/"
    file_path = path + "bonitete_tutor.tab"
    
    learning_data = Table(file_path)
    learner = abrules.ABRuleLearner()
    learner.calculate_evds(learning_data)

    return learner, learning_data

# http://localhost:8000/api/learning-rules/    
def learningRules():
    learner, learning_data = learnerAndLearningData()
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

# http://localhost:8000/api/critical-instances/
def criticalInstances():
    learner, learning_data = learnerAndLearningData()
    crit_ind, problematic, problematic_rules = argumentation.find_critical(learner, learning_data)

    # Extract the critical example from the original dataset
    critical_instances = learning_data[crit_ind]
    domains = [str(element) for element in critical_instances.domain]

    pairs = []
    detail_data = []
    for instance in critical_instances[-5:]:
        for d in domains:
            pairs.append((d, str(instance[d])))
        detail_data.append(pairs)
        pairs = []
    
    critical_instances_list = []
    for index, instance in enumerate(critical_instances[-5:]):
        critical_instances_list.append({
            "index": index+1,
            "credit_score": str(instance["credit.score"]),
            "activity_ime": str(instance["activity.ime"])
        })
    return critical_instances_list, detail_data

# http://localhost:8000/api/counter-examples/
def getCriticalExamples(critical_index, user_argument, sign):
    learner, learning_data = learnerAndLearningData()
    if user_argument not in learning_data.domain:
        return "Not correct argument"
    
    getIndex = learning_data.domain.index(user_argument)
    attribute = learning_data.domain[getIndex]
    if attribute.is_continuous:
        if sign not in (">=", "<="):
            return "Not correct argument.. missing high, low"
        user_argument += sign

    # change it to format {argument}
    formatedArg = "{{{}}}".format(user_argument)
    # add argument to argument column in row critical_index
    addArgumentToColumn(critical_index + 3, formatedArg)
    learner, learning_data = learnerAndLearningData()

    counters, counters_vals, rule, prune = argumentation.analyze_argument(learner, learning_data, critical_index)
    
    critical_examples = []
    if len(counters) > 0:
        counter_examples = learning_data[list(counters)]
        for counterEx in counter_examples:
            critical_examples.append({"activity_ime": str(counterEx["activity.ime"])})
        else:
            print("No counter examples found for the analyzed example.")

    return critical_examples

def main():
    """
    Main function, which contains the ABML interactive loop.
    """

    path = os.getcwd() + "/backend/orange3_abml_master/orangecontrib/abml/data/"
    file_path = path + "bonitete_tutor.tab"

    input("Ready to learn? Press enter")

    # MAIN LOOP
    while True:
        # learn
        stars_with_header("Learning rules...")
        learning_data = Table(file_path)
        learner = abrules.ABRuleLearner()
        learner.calculate_evds(learner)
        classifier = learner(learning_data)

        for rule in classifier.rule_list:
            print(rule.curr_class_dist.tolist(), rule, rule.quality)
        print()

        # critical examples
        stars_with_header("Finding critical examples...")
        crit_ind, problematic, problematic_rules = argumentation.find_critical(learner, learning_data)

        # Extract the critical example from the original dataset
        critical_instances = learning_data[crit_ind]
        print("Critical instances:")
        for index, instance in enumerate(critical_instances[:5]):
            print(index+1, " -> ", instance["credit.score"], " ", instance["activity.ime"])
            
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
        critical_index = int(selectedInstanceIndex) - 1

        while True:
            # input argument
            stars_with_header("Argument input...")

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
            # add argument to argument column in row critical_index
            addArgumentToColumn(file_path, critical_index + 3, formatedArg)
            learning_data = Table(file_path)
            learner = abrules.ABRuleLearner()
            learner.calculate_evds(learning_data)

            input("Press enter for argument analysis")

            stars_with_header("Analysing argument...")
            counters, counters_vals, rule, prune = argumentation.analyze_argument(learner, learning_data, critical_index)
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
                removeArgumentFromColumn(file_path, critical_index + 3)
            if inp == 'd':
                # show which critical example was done in this iteration
                critical_instance = learning_data[critical_index]
                print("This iteration critical example:", critical_instance)
                break

        # increment iteration
        stars_with_header("Next iteration:")

    return 0


if __name__ == '__main__':
    status = main()