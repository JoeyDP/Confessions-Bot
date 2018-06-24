from pandas import DataFrame
from database import Confession


# labels for classification
POSTED = 'posted'
REJECTED = 'rejected'

CLASSES = [POSTED, REJECTED]

FRESH = 'fresh'
PAGE_ID = '595906520554969'


def build_data_frame(confessions, classification=None):
    """ Create pandas data frame from file and class. """
    rows = []
    for confession in confessions:
        data = {'text': confession.text}
        if classification:
            data['class'] = classification
        rows.append(data)

    data_frame = DataFrame(rows)
    return data_frame


def getTrainData():
    data = DataFrame({'text': [], 'class': []})
    for label in CLASSES:
        confessions = Confession.findByStatusAndPage(label, PAGE_ID)
        # confessions = Confession.findByStatus(label)
        data = data.append(build_data_frame(confessions, label))

    return data


def getFreshData():
    data = DataFrame({'text': []})
    confessions = Confession.findByStatusAndPage(FRESH, PAGE_ID)
    # confessions = Confession.findByStatus(FRESH)
    data = data.append(build_data_frame(confessions))
    return data

