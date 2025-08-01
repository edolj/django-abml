""" Module implements finding critical examples and analysis of arguments.
"""

import numpy as np
import Orange
from . import abrules
from Orange.data import Table
from Orange.classification.rules import Rule, Selector
from sklearn.model_selection import StratifiedKFold
from scipy.spatial.distance import pdist, squareform

ARGUMENTS = "Arguments"
SIMILAR = 30

def kmeans(dist, weights, initial):
    """ Implements weighted kmeans clustering. """
    centers = initial
    cent_set = set()
    steps = 0
    while str(centers) not in cent_set and steps < 100:
        cent_set.add(str(centers))
        steps += 1
        # compute clusters that belong to each center
        weighted = dist[centers]*weights
        mins = np.argmin(weighted, 0)
        # recalulate centers
        new_centers = []
        for i in range(len(centers)):
            ind = mins == i
            if not np.any(ind):
                # Skip empty cluster or handle it in some way
                continue
            # select only instances belonging to this cluster
            seldist = dist[np.ix_(ind, ind)]*weights[ind]
            # central cluster is the one having the smallest distance sum to others
            ind_vals = np.where(ind)[0]
            central = ind_vals[np.argmin(seldist.sum(1))]
            new_centers.append(central)
        centers = new_centers
    return centers

def relative_freq(rule):
    """ Classification accuracy of rule measured with relative frequency. """
    dist = rule.curr_class_dist
    return dist[rule.target_class] / dist.sum()

def coverage(rules, data):
    coverages = np.zeros((len(data), len(rules)), dtype=bool)
    for ri, r in enumerate(rules):
        coverages[:, ri] = r.evaluate_data(data.X)
    return coverages

def find_critical(learner, data, n=5, k=5, random_state=0):
    """
    :param learner: argument-based learner to be tested
    :param data: learning data
    :param n: number of critical examples
    :param k: folds in cross-validation
    :param random_state: random state to be used in StratifiedKFold function
    :return: n most critical examples (with estimation of 'criticality')
    """
    # first get how problematic is each example (cross-validation)
    # E ... the difference between probability of predicted most probable class
    # and the probability of the example's class.
    # if example is correctly predicted or if example is already covered
    # by an argumented rule, E equals 0.
    # CV
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=random_state)
    problematic = np.zeros(len(data))
    problematic_rules = [[] for d in data]
    for learn_ind, test_ind in skf.split(data.X, data.Y):
        # move test_ind with arguments to learn_ind
        arg_ind = []
        if ARGUMENTS in data.domain:
            for t in test_ind:
                if data[t][ARGUMENTS] not in ("", "?"):
                    arg_ind.append(t)
        learn_ind = np.array(sorted(list(learn_ind)+arg_ind), dtype=int)
        test_ind = np.array([t for t in test_ind if t not in arg_ind], dtype=int)
        learn = Table.from_table(data.domain, data[learn_ind])
        test = Table.from_table(data.domain, data[test_ind])

        classifier = learner(learn)
        rules = classifier.rule_list
        # eval rules on test data
        cov = coverage(rules, test)

        # for each test instance find out best covering rule from the same class
        best_covered = np.zeros(len(test))
        for ri, r in enumerate(rules):
            target = r.target_class == test.Y
            best_covered = np.maximum(best_covered, (cov[:, ri] & target) * r.quality)

        # compute how problematic each instance is ...
        probs = classifier(test, 1)
        for ti, t in enumerate(test_ind):
            # first check best rule, if same class, it can not be problematic
            d, p = test[ti], probs[ti]
            c = int(d.get_class())
            # find best rule covering this example (best_rule * prediction)
            problematic[t] = (1 - best_covered[ti]) * (1 - p[c])
            problematic_rules[t] = [r for ri, r in enumerate(rules) if cov[ti, ri]]

    # compute Mahalanobis distance between instances
    dist_matrix = squareform(pdist(data.X, metric="seuclidean"))

    # criticality is a combination of how much is the instance problematic
    # and its distance to other problematic examples of the same class
    # for loop over classes
    vals = np.unique(data.Y.astype(dtype=int))
    k = int(np.ceil(n/len(vals)))
    crit_ind = []
    for i in vals:
        inst = (data.Y == i) & (problematic > 1e-6)
        inst_pos = np.where(inst)[0]
        wdist = dist_matrix[np.ix_(inst, inst)]
        # select k most problematic instances
        prob = problematic[inst]
        ind = np.argpartition(prob, -k)[-k:]
        centers = kmeans(wdist, prob, ind)
        for c in centers:
            crit_ind.append(inst_pos[c])

    # sort critical indices given problematicness
    crit_ind = sorted(crit_ind, key=lambda x: -problematic[x])

    return (crit_ind, problematic[crit_ind],
            [problematic_rules[i] for i in crit_ind])

def analyze_argument(learner, data, index):
    """
    Analysing argumented example consists of finding counter examples,
    suggesting "safe" or "consistent" conditions and argument pruning.

    :param learner: argument-based learner to be tested
    :param data: learning data
    :param index: index of argumented example
    :return: counter examples, suggested conditions, results of pruning rule
        that was learned from argumented example.
    """

    # learn rules; find best rule for each example (this will be needed to
    # select most relevant counters)
    X, Y, W = data.X, data.Y.astype(dtype=int), data.W if data.W else None
    clrules = learner(data)
    predictions = clrules(data, 1)
    prob_errors = 1 - predictions[range(Y.shape[0]), list(Y)]

    learner.target_instances = [index]
    rules = learner(data).rule_list
    learner.target_instances = None
    
    if not rules:
        raise ValueError("No rules generated for the given example.")
    
    rule = rules[0]
    # print(rule, rule.curr_class_dist, rule.quality)
    counters = rule.covered_examples & (Y != rule.target_class)
    counters = np.where(counters)[0]
    counter_errs = prob_errors[counters]
    cnt_zip = list(zip(counter_errs, counters))
    cnt_zip.sort()
    if cnt_zip:
        counters_vals, counters = zip(*cnt_zip)
    else:
        # Handle the case where no counterexamples were found
        counters_vals = []
        counters = []
        #print("No counter examples found for the analyzed example.")
    
    if len(rule.selectors) == 0:
        prune = [(None, 0)]
    else:
        prune = []
        for sel in rule.selectors:
            # create a rule without this selector
            tmp_rule = Orange.classification.rules.Rule(selectors=[r for r in rule.selectors if r != sel],
                                                        domain=data.domain)
            tmp_rule.filter_and_store(X, Y, W, rule.target_class)
            tmp_rule.prior_class_dist = rule.prior_class_dist
            tmp_rule.create_model()

            tmp_m_score = learner.evaluator_norm.evaluate_rule(tmp_rule)
            prune.append((tmp_rule, tmp_m_score))

    # Determine the best pruned rule
    best_pruned_rule, best_pruned_score = max(prune, key=lambda x: x[1])

    # Extending the full rule with new attributes
    unused_attributes = get_unused_attributes(rule, data)
    extended_rules = generateExtendedRules(rule, unused_attributes, data, index)
    evaluated_extended_rules = evaluate_rules(learner, extended_rules, X, Y, W, rule.target_class)
    # Determine the best extended rule
    best_extended_rule, best_extended_score = max(evaluated_extended_rules, key=lambda x: x[1])

    # ext rule has better quality
    if best_pruned_score < best_extended_score:
        best_rule = best_extended_rule
    else:
        best_rule = best_pruned_rule

    return rule, counters, best_rule

def get_unused_attributes(rule, data):
    attUsed = []
    for sel in rule.selectors:
        attUsed.append(data.domain[sel.column])

    class_var = data.domain.class_var
    attributes = get_categorical_and_numerical_attributes(data.domain)
    filtered_attributes = [attr for attr in attributes if attr not in attUsed and attr != class_var]

    return filtered_attributes

def generateExtendedRules(rule, unused_att, data, index):
    ext_rules = []

    for att in unused_att:
        column = data.domain.attributes.index(att)

        # Get the value of this attribute in the current example
        ex_value = data[index][column]

        if att.is_discrete:
            # Get index of value in domain
            value_name = ex_value.value
            if value_name not in att.values:
                continue  # skip unknown or missing values
            value_index = att.values.index(value_name)

            # Equality selector
            selector_eq = Selector(column=column, op="==", value=value_index)
            new_rule_eq = Rule(selectors=[selector_eq] + rule.selectors, domain=data.domain)
            new_rule_eq.prior_class_dist = rule.prior_class_dist
            ext_rules.append(new_rule_eq)

        elif att.is_continuous:
            value = ex_value

            # "<=" selector
            selector_le = Selector(column=column, op="<=", value=value)
            new_rule_le = Rule(selectors=[selector_le] + rule.selectors, domain=data.domain)
            new_rule_le.prior_class_dist = rule.prior_class_dist
            ext_rules.append(new_rule_le)

            # ">=" selector
            selector_ge = Selector(column=column, op=">=", value=value)
            new_rule_ge = Rule(selectors=[selector_ge] + rule.selectors, domain=data.domain)
            new_rule_ge.prior_class_dist = rule.prior_class_dist
            ext_rules.append(new_rule_ge)

    return ext_rules

def evaluate_rules(learner, rules, X, Y, W, target_class):
    evaluated_rules = [(None, 0)]
    for rule in rules:
        rule.filter_and_store(X, Y, W, target_class)
        rule.create_model()
        ext_m_score = learner.evaluator_norm.evaluate_rule(rule)
        evaluated_rules.append((rule, ext_m_score))
    return evaluated_rules

def get_categorical_and_numerical_attributes(domain):
    categorical_and_numerical_attributes = []
    for attribute in domain:
        if attribute.is_continuous or attribute.is_discrete:
            categorical_and_numerical_attributes.append(attribute)
    return categorical_and_numerical_attributes

