import pickle
import Orange
from Orange.data import Table
from Orange.evaluation import TestOnTestData, CA, AUC, LogLoss
import orangecontrib.evcrules.logistic as logistic
import orangecontrib.abml.abrules as rules
import orangecontrib.abml.argumentation as arg
from sklearn.model_selection import train_test_split

bayes = Orange.classification.NaiveBayesLearner()
logistic_lr = Orange.classification.LogisticRegressionLearner()
random_forest = Orange.classification.RandomForestLearner()
svm = Orange.classification.SVMLearner()
tree = Orange.classification.TreeLearner()
cn2 = Orange.classification.rules.CN2UnorderedLearner()

def evaluate_learners(rule_learner, data, test_size=0.2, random_state=0):
    """
    Evaluate learners on a train/test split of the data.
    """
    train_idx, test_idx = train_test_split(
        range(len(data)),
        test_size=test_size,
        random_state=random_state,
        stratify=[ex.get_class() for ex in data]
    )

    train_data = data[train_idx]
    test_data = data[test_idx]

    learner = logistic.LRRulesLearner(rule_learner=rule_learner, penalty=1)
    learners = [learner, logistic_lr, tree, bayes, cn2, random_forest, svm]

    results = TestOnTestData(train_data, test_data, learners)
    ca = CA(results)
    auc = AUC(results)

    names = ['logrules', 'logistic', 'tree', 'naive-bayes', 'cn2', 'random-forest', 'svm']
    scores = "CA\tAUC\tMethod\n"
    for ni, n in enumerate(names):
        scores += f"{ca[ni]:.3f}\t{auc[ni]:.3f}\t{n}\n"

    return scores

def split(data, critical_index, test_size=0.2, random_state=0):
    """
    Stratified split ensuring the critical example is in training set.
    Returns train/test datasets and original indices mapping.
    """
    other_indices = [i for i in range(len(data)) if i != critical_index]
    
    train_idx, test_idx = train_test_split(
        other_indices,
        test_size=test_size,
        random_state=random_state,
        stratify=[data[i].get_class() for i in other_indices]
    )
    
    train_idx.append(critical_index)
        
    train_data = data[train_idx]
    test_data = data[test_idx]

    return train_data, test_data, train_idx, test_idx

# # settings
# optimize_penalty = False # do this only once, then set the value as fixed
# cycle = 1

# # create learner
# rule_learner = rules.ABRuleLearner(add_sub_rules=True)
# rule_learner.evds = pickle.load(open("evds.pickle", "rb"))
# learner = logistic.LRRulesLearner(rule_learner=rule_learner)

# # load data
# data = Orange.data.Table('learndata')

# if optimize_penalty:
#     l1 = logistic.LRRulesLearner(opt_penalty=True)
#     print("Best penalty is: ", l1.penalty)
# learner.penalty = 1 # result of optimization

# # learn a classifier
# classifier = learner(data)

# # save model
# print(classifier)
# fmodel = open("model.txt".format(cycle), "wt")
# fmodel.write(str(classifier))

# # test model + other methods
# testdata = Orange.data.Table('testdata')
# bayes = Orange.classification.NaiveBayesLearner()
# logistic = Orange.classification.LogisticRegressionLearner()
# random_forest = Orange.classification.RandomForestLearner()
# svm = Orange.classification.SVMLearner()
# tree = Orange.classification.TreeLearner()
# cn2 = Orange.classification.rules.CN2UnorderedLearner()
# learners = [learner, logistic, tree, bayes, cn2, random_forest, svm]
# res = TestOnTestData(data, testdata, learners)
# ca = CA(res)
# auc = AUC(res)
# ll = LogLoss(res)

# names = ['logrules', 'logistic', 'tree', 'naive-bayes', 'cn2', 'random-forest', 'svm']
# scores = ""
# scores += "CA\tAUC\tLogLoss\tMethod\n"
# for ni, n in enumerate(names):
#     scores += "{}\t{}\t{}\t{}\n".format(ca[ni], auc[ni], ll[ni], n)
# print(scores)
# fscores = open("scores.txt", "wt")
# fscores.write(scores)

# # find critical examples
# indices, criticality, rules = arg.find_critical(learner, data)

# for prob_i, index in enumerate(indices):
#     print("Criticality: ", criticality[prob_i], "index: ", index)
#     print(data[index])
