"""
Fetches all fields for the specified submissions on reddit and stores it into a CSV file.

Example Usage:
    python reddit_fetcher.py --start=0 --end=200 --columns='internal_id,id,subreddit' --output_prefix="output"

Note there is a special field added, "internal_id", that is the integer value of base36 encoded reddit id.
"""

# Explaining this black magic:
# http://stackoverflow.com/questions/3828723/why-we-need-sys-setdefaultencodingutf-8-in-a-py-script
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

# import codecs
import csv
import gflags
import praw
import time

from secret import REDDIT_USER_AGENT
from reddit_common import Submission
from reddit_common import submission_to_unicode


FLAGS = gflags.FLAGS
gflags.DEFINE_string('start_ts', None, 'Start fetching from timestamp.')
gflags.DEFINE_string('end_ts', None, 'End fetching at timestamp')
gflags.DEFINE_integer('step_days', 15, 'Fetch submissions in batches of step_days')
gflags.DEFINE_string('subreddits', '', 'CSV list of subreddits to fetch')
gflags.DEFINE_string('output_prefix', None, 'Location and file prefix of output CSV')

gflags.MarkFlagAsRequired('start_ts')
gflags.MarkFlagAsRequired('end_ts')
gflags.MarkFlagAsRequired('output_prefix')
gflags.MarkFlagAsRequired('subreddits')

# Constants
MAX_SUBMISSIONS_PER_QUERY = 100
# If the number of results > RESULTS_CORRECTNESS_CHECK, you should probably
# reduce --step_days. Reddit limits the number of results to ~1000, so to not
# truncate our results, we have this correctness check in place
RESULTS_CORRECTNESS_CHECK = 900

SECONDS_IN_A_DAY = 60 * 60 * 24

def epoch_to_date_string(epoch):
    # pattern = '%Y-%m-%d %H:%M:%S'
    pattern = '%Y-%m-%d'
    return time.strftime(pattern, time.localtime(epoch))

def date_to_epoch(date_str):
    pattern = '%Y-%m-%d'
    return int(time.mktime(time.strptime(date_str, pattern)))

def fetch_submissions(start_epoch, end_epoch, subreddits, csv_writer):
    r = praw.Reddit(user_agent=REDDIT_USER_AGENT)
    seconds_to_increment = SECONDS_IN_A_DAY * FLAGS.step_days
    total_records_fetched = 0
    for subreddit in subreddits:
        for i in xrange(start_epoch, end_epoch, seconds_to_increment):
            segment_start = i
            segment_end = segment_start + min(seconds_to_increment, end_epoch - i)
            query = 'timestamp:%d..%d' % (segment_start, segment_end)
            results = list(r.search(query, subreddit=subreddit,
                                    sort='new', limit=None,
                                    syntax='cloudsearch'))
            if len(results) > RESULTS_CORRECTNESS_CHECK:
                print ("WARNING: received %i results. This is dangerously close"
                       "to the max number of allowed results (1000)." % (
                           len(results)))
            for result in results:
                # We store the score as a string because we will have to write
                # it.
                submission = Submission(
                    result.id, result.title, result.selftext, result.url,
                    result.permalink, unicode(result.score), subreddit)

                # submission = submission_fields_as_strings(submission)
                # unicode_row = [s.encode('utf-8') for s in submission]
                unicode_row = submission_to_unicode(submission)
                csv_writer.writerow(unicode_row)
            total_records_fetched += len(results)
            segment_start_string = epoch_to_date_string(segment_start)
            segment_end_string = epoch_to_date_string(segment_end)
            print "[%s] - from %s to %s fetched %i results. Total submissions saved: %i" % (
                subreddit, segment_start_string, segment_end_string, len(results),
                total_records_fetched)


def main(argv):
    argv = FLAGS(argv)  # parse flags
    output_file = FLAGS.output_prefix + '-' + FLAGS.start_ts + '-to-' + FLAGS.end_ts + '.csv'
    start_epoch = date_to_epoch(FLAGS.start_ts)
    end_epoch = date_to_epoch(FLAGS.end_ts)
    subreddits = FLAGS.subreddits.split(',')
    with open(output_file, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(Submission._fields)
        fetch_submissions(start_epoch, end_epoch, subreddits, csv_writer)




if __name__ == '__main__':
    main(sys.argv)
