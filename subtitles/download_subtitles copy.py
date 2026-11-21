
from datetime import timedelta

from babelfish import Language
from subliminal import *
import os

MOVIES_PATH = os.path.join(r'S:\Movies')

# configure the cache
region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})

# iterate through movie paths and get a list of all folders as paths. 

all_movie_paths = []
for root, dirs, files in os.walk(MOVIES_PATH):
    for name in dirs:
        all_movie_paths.append(os.path.join(root, name))

# iterate through all movie paths and download subtitles for each movie.
for movie_path in all_movie_paths:
    print("Movie path: ", movie_path)
    videos = []
    # look for video files / .mp4 or .mkv files manually
    for root, dirs, files in os.walk(movie_path):
        for name in files:
            if name.endswith((".mp4", ".mkv")):
                video = Video.fromname(name)
                videos.append(video)


    subtitles = download_best_subtitles(videos, {Language('eng')})
    for v in videos:
        print(f"Found subtitles for {v.name}: {subtitles.get(v)}")
        save_subtitles(v, subtitles[v])