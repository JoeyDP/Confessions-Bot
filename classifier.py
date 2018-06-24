import itertools
import numpy as np

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from sklearn.externals import joblib

import bacli

from dataSource import getTrainData, getFreshData, CLASSES

import matplotlib.pyplot as plt


bacli.setDescription("Data mining tools for Confessions")


@bacli.command
def train():
    """ Train an store classifier. """
    vectorizer = CountVectorizer(ngram_range=(1, 2),
                                 stop_words='english',
                                 strip_accents='unicode'
                                 )

    classifier = MultinomialNB()

    pipeline = Pipeline([
        ('vectorizer', vectorizer),
        ('classifier', classifier)
    ])

    data = getTrainData()
    x = data['text'].values
    y = data['class'].values

    y_pred = cv(x, y, pipeline)
    conf_mat = confusion_matrix(y, y_pred)

    print('Total confessions classified:', len(data))
    plot_confusion_matrix(conf_mat, CLASSES)

    pipeline.fit(x, y)
    joblib.dump(pipeline, "model.pkl")


@bacli.command
def run(modelFile='model.pkl'):
    """ Load classifier and classify fresh. """
    pipeline = joblib.load(modelFile)

    data = getFreshData()
    if len(data) == 0:
        print("No fresh confessions")
        return
    x = data['text'].values
    y = pipeline.predict_proba(x)

    for sample, scores in zip(x, y):
        print(sample)
        label, score = getBestLabelScore(scores)
        print("{:.2f}\t{}".format(score*100, label))


def getBestLabelScore(scores):
    bestIndex = max(enumerate(scores), key=lambda x: x[1])[0]
    return CLASSES[bestIndex], scores[bestIndex]


def cv(x, y, classifier):
    """ Get labels of all samples using StratifiedKFold cross validation. """
    print("Cross validating")
    k_fold = StratifiedKFold(shuffle=True, n_splits=8)
    y_pred = cross_val_predict(classifier, x, y, cv=k_fold, n_jobs=-1)

    return y_pred


def cv_score(x, y, classifier):
    """ Get scores of all samples using StratifiedKFold cross validation. """
    print("Cross validate scores")
    k_fold = StratifiedKFold(shuffle=True, n_splits=8)
    y_pred = cross_val_predict(classifier, x, y, cv=k_fold, method='predict_proba')

    return y_pred


def plot_confusion_matrix(cm, p_labels=None, title='Confusion matrix', cmap=plt.cm.Blues):
    """ This function prints and plots the confusion matrix. """

    print('Confusion matrix, without normalization')
    print(cm)

    plt.figure()
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    plt.xticks(np.arange(len(p_labels)), p_labels, rotation=45)
    plt.yticks(np.arange(len(p_labels)), p_labels)

    fmt = 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.show()


