from collections import namedtuple

Submission = namedtuple('Submission', 'id title selftext url permalink score subreddit')
ProcessedSubmission = namedtuple('ProcessedSubmission', 'complete height_in start_weight_lbs end_weight_lbs gender_is_female age imgur_images imgur_albums id title selftext url permalink score subreddit')
FinalEntry = namedtuple('FinalEntry', 'id previous_weight_lbs current_weight_lbs height_in gender score title photos first_image_aspect_ratio')

"""
def submission_fields_as_strings(s):
    score = unicode(s.score)
    return Submission(s.id, s.title, s.selftext, s.url, s.permalink,
                      score, s.subreddit)
"""

def submission_to_unicode(s):
    # this is not named properly. This is submission to utf-8 encoded
    return s  # actually this function may not be needed
    # This function is a no-op at the moment

    ####
    unicode_row = []
    for field in s:
        val = field
        if isinstance(field, unicode):
            val = field.encode('utf-8')
        unicode_row.append(val)
    return unicode_row
# def processed_submission_fields_as_strings(s):



def submission_from_csv_row(row_mutable):
    # TODO: parse this here
    row = row_mutable[:]
    row[5] = int(row[5])
    return Submission(*row)

def csv_to_list(s):
    l = s.split(',')
    # http://stackoverflow.com/questions/3845423/remove-empty-strings-from-a-list-of-strings
    l = filter(None, l)
    return l

def bool_string_to_boolean(bool_string):
    assert (bool_string == 'True' or bool_string == 'False')
    if bool_string == 'True':
        return True
    if bool_string == 'False':
        return False

def processed_submission_from_csv_row(row_mutable):
    row = row_mutable[:]
    row[0] = bool_string_to_boolean(row[0])
    row[1] = int(row[1])
    row[2] = int(row[2])
    row[3] = int(row[3])
    row[4] = bool_string_to_boolean(row[4])
    # age is optional, so we special case it
    if row[5] != '':
        row[5] = int(row[5])  # age
    else:
        row[5] = None
    row[6] = csv_to_list(row[6])
    row[7] = csv_to_list(row[7])
    row[13] = int(row[13])
    return ProcessedSubmission(*row)
