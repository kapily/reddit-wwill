# Subreddits we are crawling and their creation date

Their creation date is important because we want to start crawling BEFORE their
creation date.

| Subreddit    | Creation date |
|--------------|---------------|
| loseit       | 2010-07-29    |
| keto         | 2010-05-27    |
| brogress     | 2013-10-14    |
| progresspics | 2011-06-23    |
| btfc         | 2011-01-15    |
| gainit       | 2011-01-05    |

Here's an example query:

python subreddit_fetcher.py --start="2010-05-01" --end="2015-08-17" --output_prefix="all_subreddits" --subreddits="loseit,keto,brogress,progresspics,btfc,gainit" --step_days="15"

Using q with this:
q --delimiter=, "select count(*) from features_extracted.csv"

Feature Extractor
python feature_extractor.py --input=<output> --output=<output>


Reasons why we aren't catching more:
- heights with cm


python feature_extractor.py --input=all_subreddits-2010-05-01-to-2015-08-17.csv --output=all_subreddits_extracted_features.csv
python generate_output.py --input=all_subreddits_extracted_features.csv --output=csv_output.csv
