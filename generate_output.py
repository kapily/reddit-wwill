import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import csv
import json
import gflags
from imgurpython import ImgurClient
from imgurpython.helpers.error import ImgurClientError
from imgurpython.helpers.error import ImgurClientRateLimitError
from reddit_common import processed_submission_from_csv_row
from reddit_common import FinalEntry
from secret import IMGUR_CLIENT_ID
from secret import IMGUR_CLIENT_SECRET
from synced_csv_dict import SyncedCSVDict

import urlparse, os

FLAGS = gflags.FLAGS
gflags.DEFINE_string('input', '', '')
gflags.DEFINE_string('output', '', '')
gflags.DEFINE_string('synced_csv_dict', 'imgur_album_images.csv', '')
gflags.DEFINE_string('synced_csv_dict_image_dimensions', 'imgur_images_dimensions.csv', '')
gflags.DEFINE_string('synced_csv_dict_image_does_not_exist', 'imgur_image_does_not_exist.csv', '')

gflags.MarkFlagAsRequired('input')
gflags.MarkFlagAsRequired('output')

imgur_client = ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)
imgur_album_images = SyncedCSVDict(FLAGS.synced_csv_dict)
imgur_image_dimensions = SyncedCSVDict(FLAGS.synced_csv_dict_image_dimensions)
imgur_image_does_not_exist = SyncedCSVDict(FLAGS.synced_csv_dict_image_does_not_exist)

def get_string_after(substr, s):
    idx = s.find(substr) + len(substr)
    return s[idx:]

def album_id_from_url(imgur_album_url):
    return get_string_after('/a/', imgur_album_url)

def image_id_from_url(imgur_url):
    # Remove the extension if there is any
    path = urlparse.urlparse(imgur_url).path
    ext = os.path.splitext(path)[1]
    if ext:
        assert ext in ('.jpg', '.png', '.gif'), ext
        imgur_url = imgur_url[:-4]
        # print "path: ", path, "ext: ", ext, "new_path: ", new_path
    return get_string_after('imgur.com/', imgur_url)

def get_images_in_album(album_id):
    assert album_id.strip() != ''
    if imgur_album_images.has_key(album_id):
        #print "Found: ", album_id, "in cache."
        # exit()
        val = imgur_album_images.get_val(album_id)
        if val.strip() == '':
            return []
        return val.split(',')
    images = []
    # Even if there's an error, we store it in our cache so that we don't have
    # to retry looking that up.
    try:
        #print "before fetching from imgur: "
        print 'fetching images for album_id: ', album_id
        images = imgur_client.get_album_images(album_id)
        #print "fetched from imgur!"
        images = [i.link for i in images]
    except ImgurClientError as e:
        print(e.error_message)
        print(e.status_code)
        pass
    except ImgurClientRateLimitError:
        print "Imgur Rate limit hit!!!!"
        print "Imgur credits:"
        print imgur_client.credits
        exit()

    # We store them in CSV format for the dictionary
    images_in_album_str = ','.join(images)
    imgur_album_images.set_val(album_id, images_in_album_str)
    return images

def get_image_width_height(image_id):
    if imgur_image_dimensions.has_key(image_id):
        width, height = [int(x) for x in imgur_image_dimensions.get_val(image_id).split(',')]
    else:
        try:
            image = imgur_client.get_image(image_id)
            width, height = image.width, image.height
            width_height_string = ','.join([str(width), str(height)])
            imgur_image_dimensions.set_val(image_id, width_height_string)
        except ImgurClientError as e:
            if e.status_code == 404:
                # image does not exist, mark it as such:
                if not imgur_image_does_not_exist.has_key(image_id):
                    imgur_image_does_not_exist.set_val(image_id, '')
            return 1, 1  # way to say that it does not exist for now


    return width, height

def js_bool_string(b):
    assert b == True or b == False
    if b == True:
        return 'true'
    return 'false'

def main(argv):
    argv = FLAGS(argv)  # parse flags
    output_json = {'results': []}
    with open(FLAGS.output, 'w') as output_file:
        csv_writer = csv.writer(output_file)
        csv_writer.writerow(FinalEntry._fields)
        with open(FLAGS.input, 'r') as f:
            csv_reader = csv.reader(f)
            csv_reader.next()  # skip the first line (headers)
            for row in csv_reader:
                processed_submission = processed_submission_from_csv_row(row)

                assert isinstance(processed_submission.imgur_albums, list)
                #print "processed_submission.imgur_albums = ", processed_submission.imgur_albums
                #print "processed_submission.imgur_images = ", processed_submission.imgur_images
                images_in_imgur_albums = []
                for album in processed_submission.imgur_albums:
                    images_in_imgur_albums.extend(get_images_in_album(album_id_from_url(album)))
                # TODO: need to standardize the photos format
                photos = images_in_imgur_albums + processed_submission.imgur_images

                if len(photos) == 0:
                    continue

                # Look at extensions
                for idx, photo in enumerate(photos):
                    photos[idx] = image_id_from_url(photo)

                # Get the width and height of the first image
                width, height = get_image_width_height(photos[0])
                first_image_aspect_ratio = float(width) / height
                if imgur_image_does_not_exist.has_key(photos[0]):
                    # No need to save it if there are no photos
                    continue


                entry = FinalEntry(
                    processed_submission.id,
                    processed_submission.start_weight_lbs,
                    processed_submission.end_weight_lbs,
                    processed_submission.height_in,
                    js_bool_string(processed_submission.gender_is_female),
                    processed_submission.score,
                    processed_submission.title,
                    ','.join(photos),
                    round(first_image_aspect_ratio,2)
                )

                csv_writer.writerow(entry)







if __name__ == '__main__':
    main(sys.argv)
