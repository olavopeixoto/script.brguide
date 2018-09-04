# -*- coding: utf-8 -*-

#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
#
# https://docs.google.com/document/d/1_rs5BXklnLqGS6g6eAjevVHsPafv4PXDCi_dAM2b7G0/edit?pli=1
#
import xbmcaddon
import xbmc
import urllib,datetime,re,urllib2
import gzip,StringIO
import workers
from strings import *

try:
    import json
except:
    import simplejson as json

GLOBOSAT_API_URL = 'http://api.vod.globosat.tv/globosatplay'
GLOBOSAT_API_AUTHORIZATION = 'token b4b4fb9581bcc0352173c23d81a26518455cc521'
GLOBOSAT_API_CHANNELS = GLOBOSAT_API_URL + '/channels.json?page=%d'
COMBATE_LIVE_URL = 'http://api.simulcast.globosat.tv/combate'
PREMIERE_24H_SIMULCAST = 'https://api-simulcast.globosat.tv/v1/premiereplay/'
THUMBS_URL = 'https://s01.video.glbimg.com/x720/%s.jpg'


class BRplayTVGuideApi():
    def __init__(self):
        self.channelList = []

    def channels(self):
        """
        Returns complete channel list ordered in channel packages.
        """

        if len(self.channelList) > 0: return self.channelList

        list = self.getLiveChannels()

        list = sorted(list, key=lambda k: k['name'])

        systime = (datetime.datetime.utcnow()).strftime('%Y%m%d%H%M%S%f')

        for i in list:
            meta = i #dict((k, v) for k, v in i.iteritems() if not v == '0')
            meta.update({'mediatype': 'video'})
            meta.update({'playcount': 0, 'overlay': 6})
            meta.update({'duration': i['duration']}) if 'duration' in i else None
            meta.update({'title': i['title']}) if 'title' in i else None
            meta.update({'tagline': i['tagline']}) if 'tagline' in i else None

            sysmeta = urllib.quote_plus(json.dumps(meta))

            if 'streamUrl' not in i:
                id_globo_videos = i['id']
                brplayprovider = i['brplayprovider'] if 'brplayprovider' in i else None
                isFolder = i['isFolder'] == 'true' if 'isFolder' in i else False

                i['streamUrl'] = 'plugin://plugin.video.brplay/?action=playlive&provider=%s&id_globo_videos=%s&isFolder=%s&meta=%s&t=%s' % (brplayprovider, id_globo_videos, isFolder, sysmeta, systime)

        self.channelList = list

        return self.channelList

    def programs(self, channelId=None, offset=None, tvdate=None):
        """
        Returns program list
        """

        programs = []

        channel = next(channel for channel in self.channels() if channel['channel_id'] == channelId)
        if channel == None: return programs

        fetch_from_oiplay = ADDON.getSetting('fetch.oiplay') == 'true'
        if fetch_from_oiplay:
            return self.getGuideFromOiPlay(channel, tvdate)

        schedule_data = []

        if channelId == 196:
            schedule_data = self.getSchedule(channel, tvdate)
        elif channelId == 1960:
            schedule_data = self.getCombatePrograms(channel, tvdate)
        elif channelId == 1986:
            schedule_data = self.getGntPrograms(channel, tvdate)
        elif channelId == 1991:
            schedule_data = self.getMultishowPrograms(channel, tvdate)
        elif channelId == 1982:
            schedule_data = self.getVivaPrograms(channel, tvdate)
        elif channelId == 1989:
            schedule_data = self.getGloobPrograms(channel, tvdate)
        elif channelId == 1984:
            schedule_data = self.getBrasilPrograms(channel, tvdate)
        elif channelId == 1983:
            schedule_data = self.getBisPrograms(channel, tvdate)
        elif channelId == 1992:
            schedule_data = self.getOffPrograms(channel, tvdate)
        elif channelId == 1981:
            schedule_data = self.getMaisPrograms(channel, tvdate)
        else:
            if channel['name'].startswith('SporTV'):
                schedule_data = self.getSportvsPrograms(channel['name'], tvdate)
            else:
                now = datetime.datetime.now()
                programs.append({
                    'description': strings(NO_DESCRIPTION),
                    'title': strings(NO_PROGRAM_AVAILABLE),
                    'begin': now - datetime.timedelta(hours=12),
                    'end': now + datetime.timedelta(hours=12),
                    'images_sixteenbynine': {
                        #'large': channel['fanart'],
                        'small': channel['logo']
                    }
                })

        for slot in schedule_data:
            programs.append({
                'description': slot['description'],
                'title': slot['title'],
                'begin': slot['begin'],
                'end': slot['end'],
                'images_sixteenbynine': {
                    #'large': slot['thumbnail_hd'],
                    'small': slot['thumbnail']
                }
            })

        return programs









    def parseDatetime(self, date_string, format):
        import time
        from datetime import datetime
        try:
            return datetime.strptime(date_string, format) + (self.getUtcDelta())
        except TypeError:
            return datetime(*(time.strptime(date_string, format)[0:6])) + (self.getUtcDelta())

    def parseIsoTimestamp(self, date_string, format = "%Y-%m-%dT%H:%M:%S.%f"):
        import time
        from datetime import datetime
        import datetime as dt
        try:
            finaldatetime = datetime.strptime(date_string[:-6], format)
        except TypeError:
            finaldatetime = datetime(*(time.strptime(date_string[:-6], format)[0:6]))

        return finaldatetime + dt.timedelta(hours=int(date_string[-6:].split(':')[0])*-1) + (self.getUtcDelta())

    def strptimeWorkaround(self, date_string, format='%Y-%m-%dT%H:%M:%S'):
        import time
        from datetime import datetime
        try:
            return datetime.strptime(date_string, format) + self.getUtcDelta()
        except TypeError:
            return datetime(*(time.strptime(date_string, format)[0:6])) + self.getUtcDelta()

    def getHtml(self, url, headers={}, post=None):
        headers.update({'Accept-Encoding': 'gzip'})
        request = urllib2.Request(url, data=post, headers=headers)
        response = urllib2.urlopen(request)
        data = response.read()

        try:
            encoding = response.info().getheader('Content-Encoding')
        except:
            encoding = None
        if encoding == 'gzip':
            data = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()

        response.close()

        cookies = response.info().getheader('Set-Cookie')
        if cookies:
            cookies = cookies.split(',')
            cookies = [re.search(r'^[^;]+', x).group() for x in cookies]
            cookies = ';'.join(cookies)

        return data, cookies

    def getJson(self, url, headers={}, post=None):

        import requests

        headers.update({'Accept-Encoding': 'gzip'})

        xbmc.log("Request JSON - URL: %s | Data: %s | Headers: %s" % (url, post, headers))

        if post:
            response = requests.post(url,
                          data=json.dumps(post),
                          headers=headers,
                          verify=False)
        else:
            response = requests.get(url,
                                     headers=headers,
                                     verify=False)

        data = response.text

        if 'application/json' in response.headers['content-type']:
            return json.loads(data)
        else:
            return []

    def getLiveChannels(self):

        live = []

        # live.append({
        #         'slug': 'bandnews',
        #         'name': 'Band News',
        #         'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/BandNews_TV_logo_2010.svg/1200px-BandNews_TV_logo_2010.svg.png',
        #         'fanart': 'https://observatoriodatelevisao.bol.uol.com.br/wp-content/uploads/2015/03/BandNews.jpg',
        #         'thumb': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/BandNews_TV_logo_2010.svg/1200px-BandNews_TV_logo_2010.svg.png',
        #         'playable': 'true',
        #         'plot': None,
        #         'id': -1,
        #         'channel_id': -1,
        #         'duration': None,
        #         'streamUrl': 'http://evcv.mm.uol.com.br:1935/band/bandnews/playlist.m3u8'
        #     })

        live.append({
            'slug': 'redetv',
            'name': 'RedeTV!',
            'logo': 'https://vignette.wikia.nocookie.net/logopedia/images/e/ec/RedeTV%21.png/revision/latest?cb=20110305125842',
            'fanart': 'https://vignette.wikia.nocookie.net/logopedia/images/e/ec/RedeTV%21.png/revision/latest?cb=20110305125842',
            'thumb': 'https://vignette.wikia.nocookie.net/logopedia/images/e/ec/RedeTV%21.png/revision/latest?cb=20110305125842',
            'playable': 'true',
            'plot': None,
            'id': -2,
            'channel_id': -2,
            'duration': None,
            'streamUrl': 'http://evpp.mm.uol.com.br/redetv1/redetv1/playlist.m3u8'
        })

        live.append({
            'slug': 'futura',
            'name': 'Futura',
            'fanart': 'http://static.futuraplay.org/img/og-image.jpg',
            'thumb': 'https://live-thumbs.video.globo.com/futura24ha/snapshot/',
            'logo': 'http://static.futuraplay.org/img/futura_tracobranco.png',
            'playable': 'true',
            'id': '4500346',
            'channel_id': 1985,
            'live': True,
            'livefeed': 'false', # use vod player
            'brplayprovider': 'globoplay',
            'anonymous': True
        })

        threads = [
            workers.Thread(self.getGloboplayLive, live),
            workers.Thread(self.getGlobosatLiveChannels, live),
            workers.Thread(self.getGlobosatPremiumLiveChannels, live),
            workers.Thread(self.getPremiereFcLiveChannel, live),
        ]
        [i.start() for i in threads]
        [i.join() for i in threads]

        return live

    def getUtcDelta(self):
        return self.getTotalHours(datetime.datetime.now() - datetime.datetime.utcnow())

    def getTotalHours(self, timedelta):
        import datetime as dt
        hours = int(round(
            ((timedelta.microseconds + (timedelta.seconds + timedelta.days * 24 * 3600) * 10 ** 6) / 10 ** 6) / 3600.0))
        return dt.timedelta(hours=hours)

    def getTotalSeconds(self, timedelta):
        return (timedelta.microseconds + (timedelta.seconds + timedelta.days * 24 * 3600) * 10 ** 6) / 10 ** 6


##### GLOBO PLAY ############

    def getGloboplayLive(self):
        live = []

        liveglobo = 4452349

        live.append({
            'slug': 'globo',
            'name': 'Globo RJ',
            'title': 'Globo RJ',
            'logo': 'https://s3.glbimg.com/v1/AUTH_180b9dd048d9434295d27c4b6dadc248/media_kit/42/f3/a1511ca14eeeca2e054c45b56e07.png',
            'fanart': ('https://s02.video.glbimg.com/x720/%s.jpg' % liveglobo),
            'thumb': 'https://s3.glbimg.com/v1/AUTH_180b9dd048d9434295d27c4b6dadc248/media_kit/42/f3/a1511ca14eeeca2e054c45b56e07.png',
            'playable': 'true',
            'plot': "Globo RJ",
            'id': liveglobo,
            'live': True,
            'channel_id': 196,
            'duration': None,
            'livefeed': 'true',
            'affiliate': 'lat=-22.970722&long=-43.182365',
            'brplayprovider': 'globoplay'
        })

        return live

    def getSchedule(self, channel, tvdate):

        # TODO: https://api.globoplay.com.br/v1/epg/2017-05-06/praca/RJ?api_key=35978230038e762dd8e21281776ab3c9
        # if tvdate.date() != datetime.datetime.now().today().date():
        #     return []

        schedule_url = "https://globoplay.globo.com/v/xhr/views/schedule.json?affiliate_slug=%s" % "rio-de-janeiro"

        slots = self.getJson(schedule_url)['schedule']['slots']

        result = []

        for slot in slots:
            beginTime = self.parseIsoTimestamp(slot['begins_at'])
            endTime = self.parseIsoTimestamp(slot['ends_at'])
            result.append({
                "title": slot['title'],
                "description": slot['description'],
                "begin": beginTime,
                "end": endTime,
                "id": re.match('/v/(\d+)/', slot['video_url']).group(1) if slot['video_url'] != None else None,
                "channel_id": 196,
                "program_id": re.match('/[^/]+/p/(\d+)/', slot['program_url']).group(1) if slot['program_url'] != None else None,
                "live_poster": slot['live_poster'],
                "thumbnail": slot['thumbnail'] or channel['logo'],
                "thumbnail_hd": slot['thumbnail_hd'] or channel['logo']
            })

        return result

    epoch = datetime.datetime.utcfromtimestamp(0)
    def getEpochTicks(self):
        return self.getTotalSeconds((datetime.datetime.utcnow() - self.epoch)) * 1000.0



###### GLOBOSAT PLAY ############

    def getPremiereFcLiveChannel(self):

        headers = {'Authorization': GLOBOSAT_API_AUTHORIZATION, 'Accept-Encoding': 'gzip'}
        live_channels = self.getJson(PREMIERE_24H_SIMULCAST, headers=headers)

        live = []

        for channel_data in live_channels:
            live_channel = {
                'slug': 'premiere-fc',
                'name': 'Premiere Clubes',
                'studio': 'Premiere Clubes',
                'title': channel_data['description'],
                'tvshowtitle': channel_data['name'],
                'sorttitle': 'Premiere Clubes',
                'logo': 'https://s2.glbimg.com/WIdwvWihBQYoarSEGxCQuNf-caQ=/s3.glbimg.com/v1/AUTH_180b9dd048d9434295d27c4b6dadc248/media_kit/7d/a4/19679ec6ed7a5eb860cd584e0cad.png',
                'clearlogo': 'https://s2.glbimg.com/WIdwvWihBQYoarSEGxCQuNf-caQ=/s3.glbimg.com/v1/AUTH_180b9dd048d9434295d27c4b6dadc248/media_kit/7d/a4/19679ec6ed7a5eb860cd584e0cad.png',
                'fanart': channel_data['image_url'],
                'thumb': channel_data['snapshot_url'],
                'playable': 'true',
                'plot': channel_data['description'],
                'id': int(channel_data['media_globovideos_id']),
                'channel_id': int(channel_data['channel']['globovideos_id']),
                'duration': int(channel_data['duration'] or 0) / 1000,
                'isFolder': 'false',
                'live': channel_data['live'],
                'livefeed': 'true',
                'brplayprovider': 'globosat'
            }

            live.append(live_channel)

        return live

    def getGlobosatLiveChannels(self):

        live = []

        page = 1
        headers = {'Authorization': GLOBOSAT_API_AUTHORIZATION}
        channel_info = self.getJson(GLOBOSAT_API_CHANNELS % page, headers=headers)
        results = channel_info['results']
        # loop through pages
        while channel_info['next'] <> None:
            page += 1
            channel_info = self.getJson(GLOBOSAT_API_CHANNELS % page, headers=headers)
            results.update(channel_info['results'])

        for result in results:
            if len(result['transmissions']) == 0: pass
            for transmission in result['transmissions']:
                fanart = transmission['items'][0]['image'] + "?v=%s" % self.getEpochTicks()
                live.append({
                            'slug': result['slug'],
                            'name': transmission['title'],
                            'title': transmission['title'],
                            'logo': result['color_logo'],
                            'fanart': fanart,
                            'thumb': result['color_logo'],
                            'playable': 'true',
                            'plot': None,
                            'id': transmission['items'][0]['id_globo_videos'],
                            'channel_id': transmission['id_channel'],
                            'id_globo': transmission['id_globo'],
                            'duration': None,
                            'brplayprovider': 'globosat'
                            })

        return live

    def getGlobosatPremiumLiveChannels(self):

        live = []

        headers = {'Authorization': GLOBOSAT_API_AUTHORIZATION}
        channel_info = self.getJson(COMBATE_LIVE_URL, headers=headers)
        results = channel_info['results']

        logo = "https://s.glbimg.com/pc/gm/media/dc0a6987403a05813a7194cd0fdb05be/2014/11/14/d19357930c6efe009ac1f8ed3a9b55aa.png"
        for result in results:

            live.append({
                        'slug': result['channel']['title'].lower(),
                        'name': result['channel']['title'],
                        'logo': logo,
                        'fanart': result['thumb_cms'],
                        'thumb': logo,
                        'playable': 'true',
                        'plot': (result['day'] or '') + ' - ' + (result['title'] or '') + ' | ' + (result['subtitle'] or ''),
                        'programTitle': result['subtitle'],
                        'id': result['id_midia_live_play'],
                        'channel_id': result['channel']['id_globo_videos'],
                        'duration': int(result['duration']) * 60,
                        'title': result['title'],
                        'tagline': result['subtitle'],
                        'datetime': self.parseDatetime(result['day'], '%d/%m/%Y %H:%M').isoformat(), #"day": "24/04/2017 21:30",
                        'brplayprovider': 'globosat'
                        })

        # premierefc_games = self.getJson("https://globosatplay.globo.com/premierefc/ao-vivo/add-on/jogos-ao-vivo/520142353f8adb4c90000008.json")['jogos']
        #
        # logo = "https://s.glbimg.com/pc/gm/media/dc0a6987403a05813a7194cd0fdb05be/2014/11/14/6f6d8aa1ea586a03272a521cf6c50bc7.png"
        # for index, game in enumerate(premierefc_games):
        #     live.append({
        #         'slug': 'premierefc',
        #         'name': 'Premiere FC ' + str((index + 1)),
        #         'title': 'Premiere FC ' + str((index + 1)),
        #         'logo': logo,
        #         'fanart': None,
        #         'thumb': logo,
        #         'playable': 'true',
        #         'plot': game['campeonato'] + ': ' + game['time_mandante']['nome'] + ' x ' + game['time_visitante']['nome'] + ' (' + game['estadio'] + '). ' + game['data'],
        #         'id': game['id_midia'],
        #         'channel_id': 'premiere-' + str((index + 1)),
        #         'duration': 180 * 60,
        #         'brplayprovider': 'globosat'
        #     })

        return live

    def getCombatePrograms(self, channel, tvdate): #1960
        schedule_url = "https://globosatplay.globo.com/combate/ao-vivo/add-on/programacao/540e009672696f2f99000000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/cbt24ha/snapshot/")

    def getGntPrograms(self, channel, tvdate): #1986
        schedule_url = "https://globosatplay.globo.com/gnt/ao-vivo/add-on/programacao/5565ce7d72696f449b0c0000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/gnt24ha/snapshot/")

    def getMultishowPrograms(self, channel, tvdate): #1991
        schedule_url = "https://globosatplay.globo.com/multishow/ao-vivo/add-on/programacao/5565ce7d72696f449b130000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/msw24ha/snapshot/")

    def getVivaPrograms(self, channel, tvdate): #1982
        schedule_url = "https://globosatplay.globo.com/viva/ao-vivo/add-on/programacao/552c2f8c72696f3954050000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/viva24ha/snapshot/")

    def getGloobPrograms(self, channel, tvdate): #1989
        schedule_url = "https://globosatplay.globo.com/gloob/ao-vivo/add-on/programacao/5565ce7d72696f449b050000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/gloob24ha/snapshot/")

    def getBrasilPrograms(self, channel, tvdate): #1984
        schedule_url = "https://globosatplay.globo.com/canal-brasil/ao-vivo/add-on/programacao/5480ab9272696f07ad050000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/bra24ha/snapshot/")

    def getBisPrograms(self, channel, tvdate): #1983
        schedule_url = "https://globosatplay.globo.com/bis/ao-vivo/add-on/programacao/5565ce7d72696f449b210000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/bis24ha/snapshot/")

    def getOffPrograms(self, channel, tvdate): #1992
        schedule_url = "https://globosatplay.globo.com/canal-off/ao-vivo/add-on/programacao/547f708072696f7a92050000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/off24ha/snapshot/")

    def getMaisPrograms(self, channel, tvdate): #1981
        schedule_url = "https://globosatplay.globo.com/globosat/ao-vivo/add-on/programacao/5565ce7d72696f449b1a0000.json"
        return self.getGlobosatPrograms(channel, tvdate, schedule_url, "https://live-thumbs.video.globo.com/maisgsat24ha/snapshot/")


    def getGlobosatPrograms(self, channel, tvdate, url, thumb):

        # if tvdate.date() != datetime.datetime.now().today().date():
        #     return []

        schedule = self.getJson(url)

        programs = []

        for idx, slot in enumerate(schedule):
            beginTime = self.parseIsoTimestamp(slot['data'])
            endTime = beginTime + datetime.timedelta(minutes=slot['duracao_minutos'])

            #thumb = thumb + "?v=%s" % str((self.getEpochTicks() + idx))
            programs.append({
                "title": slot['nome'], #channel['name'],
                "description": slot['nome'] + (" Ao Vivo" if slot['ao_vivo'] == True or slot['ao_vivo'] == 'true' else ''),
                "begin": beginTime,
                "end": endTime,
                "live_poster": None,
                "thumbnail": thumb,
                "thumbnail_hd": thumb
            })

        return programs


    def getSportvsPrograms(self, channel_name, tvdate):
        if tvdate.date() != datetime.datetime.now().today().date():
            return []

        schedule = self.getJson("https://globosatplay.globo.com/api/v1/sportv/live-signals.json")

        programs = []

        for channel in schedule:
            if channel['title'] == channel_name:
                channel = channel
                break

        schedule = channel['schedule']

        thumb = channel['thumbUrl'] + "?v=%s" % self.getEpochTicks()

        for slot in schedule:
            beginTime = self.parseIsoTimestamp(slot['startsAt'], "%Y-%m-%dT%H:%M:%S")
            endTime = beginTime + datetime.timedelta(minutes=slot['durationInMinutes'])
            programs.append({
                "title": slot['title'] + (" Ao Vivo" if slot['live'] == True else ''),
                "description": slot['description'],
                "begin": beginTime,
                "end": endTime,
                "live_poster": None,
                "thumbnail": thumb,
                "thumbnail_hd": thumb
            })

        return programs



    channel_programs = {}
    def getGuideFromOiPlay(self, channel_info, original_date):

        channel_name = channel_info['name']
        channel_name = channel_name.lower().replace(' rj', '').replace('studio universal', 'universal channel')

        xbmc.log("Finding guide for channel: '%s' and date: '%s'" % (channel_name, original_date))

        gmtOffset = 3

        tvdate = original_date - self.getUtcDelta() - datetime.timedelta(hours=gmtOffset) + datetime.timedelta(hours=20)
        tvdatebefore = original_date - self.getUtcDelta() - datetime.timedelta(hours=gmtOffset) - datetime.timedelta(hours=4)

        date = datetime.datetime.strftime(tvdate, '%Y-%m-%d %H:%M')
        datebefore = datetime.datetime.strftime(tvdatebefore, '%Y-%m-%d %H:%M')

        if len(self.channel_programs) > 0:
            if channel_name in self.channel_programs and date in self.channel_programs[channel_name]:
                xbmc.log("Found program data in cache")
                return self.channel_programs[channel_name][date]
            elif not channel_name in self.channel_programs:
                xbmc.log("Channel program data not found")
                return []

        xbmc.log("Fetching channel program data from source for date '%s'. From: '%s' to '%s'" % (original_date, datebefore, date))

        url = 'https://apinew-cr-oi-prod-bs.sf.vubiquity.com/v2/epg-items/search'

        response = self.getJson(url, headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Affiliate-Id': '15'},
                             post={
                                 'FilterTimeStart': datebefore,
                                 'FilterTimeEnd': date
                             })

        guide = response['Data']

        channels = [channel['name'].lower() for channel in self.channels()]
        # channels.append('universal channel')
        for channel in list(channels):
            if channel.endswith(' rj'):
                channels.append(channel.replace(' rj', ''))

        for guide_channel in guide:
            guide_channel_name = guide_channel['TvStationName'].lower().replace(' hd', '')\
                .replace('+ globosat', 'mais globosat')\
                .replace('off', 'canal off')\
                .replace('universal channel', 'universal')\
                .replace('globo news', 'globonews')\
                .replace('sportv2', 'sportv 2')\
                .replace('sportv3', 'sportv 3')\
                .replace('globo rio', 'globo')

            if not guide_channel_name in channels:
                continue

            #channel_logo = guide_channel['image']
            date_programs = self.channel_programs[guide_channel_name] if guide_channel_name in self.channel_programs else {}
            programs = date_programs[date] if date in date_programs else []
            for schedule in guide_channel['Events']:
                program_thumb = schedule['AssetUrl'] if 'AssetUrl' in schedule else None
                program_poster = schedule['TVStationLogoUrl']
                channel_logo = program_poster
                program_fanart = schedule['AssetUrl'] if 'AssetUrl' in schedule else None
                program_name = schedule['Title']
                program_genre = schedule['Genres'][0] if 'Genres' in schedule and len(schedule['Genres']) > 0 else 'No Genre'
                episode_description = schedule['LongSynopsis'] if 'LongSynopsis' in schedule else ''

                start_date = schedule['TimeStart']
                end_date = schedule['TimeEnd']

                beginTime = self.strptimeWorkaround(start_date, format='%Y-%m-%d %H:%M') + datetime.timedelta(hours=gmtOffset)
                endTime = self.strptimeWorkaround(end_date, format='%Y-%m-%d %H:%M') + datetime.timedelta(hours=gmtOffset)

                programs.append({
                    "title": program_name,
                    "description": program_genre + u' - ' + episode_description,
                    "begin": beginTime,
                    "end": endTime,
                    "logo": channel_logo,
                    "live_poster": program_poster,
                    "thumbnail": program_thumb,
                    "thumbnail_hd": program_fanart,
                    'images_sixteenbynine': {
                        #'large': program_fanart,
                        'small': program_thumb
                    }
                })

            date_programs.update({date: programs})
            self.channel_programs.update({guide_channel_name: date_programs})

        return self.channel_programs[channel_name][date]