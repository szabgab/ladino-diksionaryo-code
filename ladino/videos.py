import os
import re
import sys


import markdown


def load_videos(path):
    path_to_md_file = os.path.join(path, 'README.md')
    with open(path_to_md_file) as fh:
        text = fh.read()
    content = markdown.markdown(text, extensions=['tables'])
    videos = []

    for filename in os.listdir(os.path.join(path, 'videos')):
        print(filename)
        with open(os.path.join(path, 'videos', filename)) as fh:
            header = {}
            in_header = False
            for line in fh:
                line = line.rstrip("\n")
                if line == '---':
                    if header:
                        break
                    in_header = True
                    continue
                field, value = line.split(':', 1)
                field = field.strip()
                value = value.strip()
                header[field] = value
            header['text'] = fh.read()
            header['filename'] = filename[:-4]

            match = re.search(r'^https://www.youtube.com/watch\?v=(.*)$', header['url'])
            if not match:
                raise Exception(f"Invalid URL {header['url']}")
            header["embed"] = "https://www.youtube.com/embed/" + match.group(1)
            videos.append(header)

    videos.sort(key=lambda video: video['data'])

    return videos, content
