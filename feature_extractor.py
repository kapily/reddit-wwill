# Explaining this black magic:
# http://stackoverflow.com/questions/3828723/why-we-need-sys-setdefaultencodingutf-8-in-a-py-script
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

# import codecs
import copy
import csv
import gflags
import re
import sys
import yaml


from reddit_common import Submission
from reddit_common import ProcessedSubmission
from reddit_common import submission_from_csv_row
from reddit_common import submission_to_unicode


FLAGS = gflags.FLAGS
gflags.DEFINE_string('input', None, 'Input file to read.')
gflags.DEFINE_string('output', None, 'Output file to write.')
gflags.DEFINE_boolean('output_only_complete', True, 'Outputs only complete rows.')
gflags.DEFINE_string('debug_id', '', 'If set, prints debug statement for the submission with the given id.')

gflags.MarkFlagAsRequired('input')
gflags.MarkFlagAsRequired('output')


MIN_REASONABLE_WEIGHT_LBS = 95
MAX_REASONABLE_WEIGHT_LBS = 700

MIN_REASONABLE_HEIGHT_IN = 53
MAX_REASONABLE_HEIGHT_IN = 108

def raw_string(s):
    # this function isn't working as expected so I'm not using it.
    # Also haven't run into any related bugs
    # Since we are working with regex's we should cast all regex's as raw_string's
    return s.encode('string-escape')

def replace_variables(s, variables):
    #s = raw_string(s)
    for key in variables:
        matcher_in_braces = r'{%s}' % (key)
        s = s.replace(matcher_in_braces, variables[key])
        #s = raw_string(s)
    return s

def process_extracted_variables(v, debug=False):
    start_weight = v.get('start_weight', None)
    end_weight = v.get('end_weight', None)

    # start_weight_lbs is the value we return ONLY if the weight parsing and
    # error checking goes smoothly. We ONLY set these values if it has been
    # parsed successfully.
    start_weight_lbs = None
    end_weight_lbs = None

    # we cast as float first because the strings might be floats.
    if start_weight:
        start_weight = int(float(start_weight))
    if end_weight:
        end_weight = int(float(end_weight))

    # A small hack - if we only have one weight, we treat it as the start and
    # end weight.
    if start_weight and not end_weight:
        end_weight = start_weight

    # if it's metric, convert it.
    if v['is_metric_weight'] and start_weight:
        start_weight = int(start_weight * 2.2)
        end_weight = int(end_weight * 2.2)

    if v['is_metric_weight'] and v['is_imperial_weight']:
        # when both are present, it's too confusing to tell which weights we
        # have parsed
        start_weight = None
        end_weight = None

    if start_weight and end_weight:
        # If weight is not EXPLICITLY metric, I think it's fair to assume
        # imperial
        if (MIN_REASONABLE_WEIGHT_LBS < start_weight < MAX_REASONABLE_WEIGHT_LBS and
            MIN_REASONABLE_WEIGHT_LBS < end_weight < MAX_REASONABLE_WEIGHT_LBS):
            start_weight_lbs = start_weight
            end_weight_lbs = end_weight
            # TODO(kapil): Need to handle metric weights

    height_in = None
    gender = v.get('gender', None)
    if isinstance(gender, basestring):
        gender = gender.lower()
    gender_is_female = None
    if gender == 'm' or gender == 'male':
        gender_is_female = False
    if gender == 'f' or gender == 'female':
        gender_is_female = True
    age = v.get('age', None)

    # Case when only height in ft is specified
    if 'height_ft' in v and not 'height_in' in v:
        height_in = int(v['height_ft']) * 12

    # Case when height in specified in feet and inches
    if 'height_in' in v and 'height_ft' in v:
        height_in = int(v['height_in']) + int(v['height_ft']) * 12

    if 'height_in' in v:
        # this means there was some sort of parsing error
        if int(v['height_in']) >= 12:
            height_in = None


    # Make sure height is reasonable
    if height_in is not None and not MIN_REASONABLE_HEIGHT_IN < height_in < MAX_REASONABLE_HEIGHT_IN:
        height_in = None

    if debug:
        print "height_in: ", height_in

    # Imgur album data is stored in a set (to remove duplicates), but we need
    # to convert it to string format for output
    imgur_images = None
    if 'imgur_images' in v:
        imgur_images = ','.join(v['imgur_images'])
    imgur_albums = None
    if 'imgur_albums' in v:
        imgur_albums = ','.join(v['imgur_albums'])

    # If all of these fields are completed, it's good enough to push
    completed = False
    if (start_weight_lbs is not None and
        end_weight_lbs is not None and
        height_in is not None and
        gender is not None and
        (imgur_images or imgur_albums)):
        completed = True

    if debug:
        print "completed =", completed

    assert height_in is None or isinstance(height_in, int)

    return (completed, height_in, start_weight_lbs, end_weight_lbs, gender_is_female, age,
            imgur_images, imgur_albums)

# Load the feature extractor from the yaml file. The main reason we have this
# function is so that we can replace the variables in the variables with the
# variables defined in the variables section
def get_feature_extractor(feature_extractor, rules_yaml, variables):
    feature_extractor = copy.deepcopy(rules_yaml[feature_extractor])
    extractor_names = feature_extractor.keys()
    for extractor_name in extractor_names:
        pattern = feature_extractor[extractor_name]['pattern']
        feature_extractor[extractor_name]['pattern'] = replace_variables(pattern, variables)
    return feature_extractor

def feature_extractors_in_order(feature_extractor_dict):
    feature_extractor_list = [None] * len(feature_extractor_dict)
    for extractor_name, extractor_dict in feature_extractor_dict.iteritems():
        order = extractor_dict['order']
        feature_extractor_list[order] = (extractor_name, extractor_dict)
    return feature_extractor_list

def run():
    # Test apparatus:
    # Open a file, read the titles, try to extract content, output CSV with
    # extracted content.

    # TODO: I would really like to move this logic into a well-designed class
    # for general-purpose .yaml based extractors.

    rules = yaml.load(open('rules.yaml', 'r'))
    variables = rules['variables']
    feature_extractors_single = get_feature_extractor('feature_extractors_single', rules, variables)
    feature_extractors_list = get_feature_extractor('feature_extractors_list', rules, variables)
    feature_extractors_boolean = get_feature_extractor('feature_extractors_boolean', rules, variables)


    input_file = open(FLAGS.input, 'r')
    output_file = open(FLAGS.output, 'w')
    csv_writer = csv.writer(output_file)
    csv_writer.writerow(ProcessedSubmission._fields)
    csv_reader = csv.reader(input_file)
    csv_reader.next()  # skip the first row because of headers
    number_completed_rows = 0
    for row in csv_reader:
        submission = submission_from_csv_row(row)
        all_extracted_variables = {}

        text_to_process = {'title': submission.title,
                           'selftext': submission.selftext,
                           'url':submission.url}
        debug_mode = False
        if FLAGS.debug_id == submission.id:
            print "Debug printing for --debug_id=%s" % (FLAGS.debug_id)
            debug_mode = True
        for location, text in text_to_process.iteritems():
            # Extract single features

            # To support unicode characters in the text we are trying to parse:
            # UGH...can't wait till gflags supports Python3...
            text = text.decode('utf-8')


            for extractor_name, extractor_dict in feature_extractors_in_order(feature_extractors_single):
                order = extractor_dict['order']
                if location not in extractor_dict['locations']:
                    continue
                pattern = extractor_dict['pattern']
                if debug_mode:
                    print "extractor [%i, %s]" % (order, extractor_name)
                    print "  text: ", text
                    print "  pattern:", pattern
                pattern = pattern.decode('utf-8')
                m = re.search(pattern, text, re.UNICODE)
                if m is not None:
                    extracted_variables = m.groupdict()
                    # We do this funky thing here because we want the existing
                    # values in all_extracted_variables to have priority over
                    # the new values we are adding. This allows us to order
                    # our feature extractors in order from most confident to
                    # least confident without worries of adding features from
                    # less confident feature extractors.
                    if debug_mode:
                        print  "  extractor returned:", extracted_variables
                    extracted_variables.update(all_extracted_variables)
                    all_extracted_variables = extracted_variables
                else:
                    if debug_mode:
                        print "  extractor returned no matches."
                if debug_mode:
                    print "----------------------------------------------"
                    # print "Extracted!", all_extracted_variables
                #print "text: ", text
                #print "pattern: ", pattern
            # Extract feature lists:
            for extractor_name, extractor_dict in feature_extractors_in_order(feature_extractors_list):
                if location not in extractor_dict['locations']:
                    continue
                pattern = extractor_dict['pattern']
                pattern = pattern.decode('utf-8')
                matches = re.findall(pattern, text, re.UNICODE)
                assert isinstance(matches, list)
                if extractor_name not in all_extracted_variables:
                    all_extracted_variables[extractor_name] = set()
                for match in matches:
                    all_extracted_variables[extractor_name].add(match)
            # Set Boolean features
            for extractor_name, extractor_dict in feature_extractors_in_order(feature_extractors_boolean):
                if location not in extractor_dict['locations']:
                    continue
                pattern = extractor_dict['pattern']
                # By default, we set all features to False
                if extractor_name not in all_extracted_variables:
                    all_extracted_variables[extractor_name] = False
                pattern = pattern.decode('utf-8')
                m = re.search(pattern, text, re.UNICODE)
                if m is not None:
                    all_extracted_variables[extractor_name] = True
        # print "all_extracted_variables: ", all_extracted_variables


        (complete, height_in, start_weight_lbs, end_weight_lbs,gender_is_female,
         age, imgur_images, imgur_albums) = process_extracted_variables(
            all_extracted_variables, debug_mode)
        if debug_mode:
            print all_extracted_variables

        if complete:
            number_completed_rows += 1
        if FLAGS.output_only_complete and not complete:
            continue
        processed_submission = ProcessedSubmission(
            complete, height_in, start_weight_lbs, end_weight_lbs, gender_is_female, age,
            imgur_images, imgur_albums, *submission)
        # Output to csv
        csv_writer.writerow(submission_to_unicode(processed_submission))
    input_file.close()
    output_file.close()
    print "number_completed_rows: ", number_completed_rows


def main(argv):
    argv = FLAGS(argv)  # parse flags
    run()

if __name__ == '__main__':
    main(sys.argv)
