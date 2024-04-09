#!/bin/python3
import argparse
import json
import os
import re
import time


class Angel:
    '''Fetcher'''
    api_head = 'https://api.animethemes.moe/'
    last_fetch_time = time.time()  # Obey API rate limit

    def fetch(api):
        '''Help you write less to fetch things from animethemes.moe'''
        Angel.ready()
        return json.loads(os.popen(f"curl -g '{api}'").read())

    def pull(link, name, skip):
        '''Download link as name.mp3'''
        # If skip, list local songs to try reduce download times
        # > name = '631MUSO'
        # > ls $name[.a-z]*
        # 631MUSO.mp3
        # 631MUSOa.mp3
        #        ^ The dot(.) and lowercase means no need to download
        if (sames := os.popen(f'ls {name}[.a-z]*').read().split()) and skip:
            return
        Angel.ready()
        if os.system(f'curl {link}|ffmpeg -i - -af loudnorm -b:a 64k'
                     f' -map_chapters -1 -map_metadata -1 -f mp3 /tmp/{name}'):
            return  # download incomplete
        if sames:
            # solve name conflicts
            sames += f'/tmp/{name}',
            mds = [''.join(chr(55+ord(c)) if c.isdigit() else c for c in
                           os.popen(f'md5sum {s}').read()) for s in sames]
            for i in range(2):  # conflict rate: 1/256
                if len(sames) == len({m[:1+i] for m in mds}):
                    for j, s in enumerate(sames):
                        os.system(f'mv {s} {name}{mds[j][:1+i]}.mp3')
                    break
        else:
            os.system(f'mv /tmp/{name} {name}.mp3')  # save

    def ready():
        '''Most websites keep a rate limit of 60 per minute'''
        if 1 > time.time() - Angel.last_fetch_time:
            time.sleep(1)
        Angel.last_fetch_time = time.time()


class AnimeSeason:
    Season = 'Winter', 'Spring', 'Summer', 'Fall'

    def __getattr__(self, name):
        if 'season' == name:
            return self.Season[self.quarter]

    def __init__(self, season=''):
        '''The first anime is on air in 1st quarter in 1963'''
        if not re.compile(r'\d\d[1-4]').match(season):
            season = '631'
        self.quarter = int(season[2]) - 1
        self.year = (y := int(season[:2])) + (1900, 2000)[63 > y]

    def __iter__(self):
        while 1:
            yield self
            self.quarter += 1
            if len(self.Season) == self.quarter:
                self.quarter = 0
                self.year += 1

    def __repr__(self):
        return f'{str(self.year)[-2:]}{1 + self.quarter}'


class AnimeAngel:
    def abbr_studio(self, slug):
        '''Short names are better on wearables
        '''
        pres = 'production', 'studio'
        full = slug.replace('_', '')  # abbr is alnum
        abbr = full[:3]
        if full.startswith(pres):
            pattern = f'({"|".join(pres)})' r'(?P<abbr>\w{,3})'
            abbr = re.compile(pattern).match(full).group('abbr')
        if 3 > (l := len(abbr)):
            abbr = f'{full[:3-l]}{abbr}'  # each abbr lens 3
        return abbr.upper()   # upper is more readable

    def clone_songs(self, since='', skip=0):
        self.skip = skip
        for when in AnimeSeason(since):
            '''pull anime songs from animethemes.moe'''
            # Use this to get animes on air in some year
            self.when = when
            self.pull('anime', {
                'fields': {
                    'anime': 'id',  # useless
                    'animetheme': 'sequence,type',  # like'1,OP'
                    'animethemeentry': 'id',  # useless
                    'audio': 'filename,size',
                    'studio': 'slug',
                    'video': 'id',  # useless
                },
                'include': (i := 'animethemes.animethemeentries.videos.audio,studios'),
                'filter': {
                    'has-and': i,
                    'season': when.season,
                    'year': when.year,
                },
            }).clone_songs_pull()

    def clone_songs_pull(self):
        for a in self.moe['anime']:
            s = ''.join(self.abbr_studio(s['slug']) for s in a['studios'])
            for t in a['animethemes']:
                e = f"{t['type'][0]}{t['sequence']or''}"
                a = [v['audio'] for e in t['animethemeentries'] for v in e['videos']]
                f = sorted(a, key=lambda a: a['size'])[0]['filename']
                link = f'https://a.animethemes.moe/{f}.ogg'
                Angel.pull(link, f'{self.when}{s}{e}', self.skip)
        if next := self.moe['links']['next']:
            self.moe = Angel.fetch(next)
            self.clone_songs_pull()

    def pull(self, endpoint, config={}):
        params = []
        for k, v in config.items():
            if type(v) is str:
                params += f'{k}={v}',
            else:
                params += (f'{k}[{s}]={w}' for s, w in v.items())
        self.moe = Angel.fetch(f'{Angel.api_head}{endpoint}'
                     f"{'?' if params else ''}{'&'.join(params)}")
        return self


if '__main__' == __name__:
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', action='store_true')
    parser.add_argument('since', default='', nargs='?')
    arg = parser.parse_args()
    AnimeAngel().clone_songs(arg.since, arg.n)